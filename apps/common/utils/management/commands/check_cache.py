# apps/common/utils/management/commands/check_cache.py
"""
Si la cache esta funcionando de verdad, y si sirve para lo que se puso.

pag no configura ``CACHES``: Django usa ``LocMemCache``, que es **por
proceso**. Lo que hay que saber no es si «responde» sino si los contadores se
comparten entre procesos, porque de eso depende que los limites de intentos
(OTP, acceso de asesores, recuperacion de clave) valgan lo que dicen. Con N
workers, un limite por proceso es N veces mas laxo, y se reinicia con cada
despliegue.

La prueba que decide es la ultima: se escribe una clave y se lee **desde otro
proceso**. Con una cache compartida (Redis, Memcached, base de datos) se ve;
con ``LocMemCache`` no. Si algun dia se configura Redis, esta comprobacion es
la que dira si de verdad se comparte, y ``django-redis`` con
``IGNORE_EXCEPTIONS`` es justo el caso en que una cache rota no da error:
``cache.get()`` devuelve ``None``, indistinguible de «esa clave no existe».

    manage.py check_cache
"""

import os
import subprocess
import sys
import time
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

#: Modo interno: el subproceso solo lee la clave y la imprime.
READ_PREFIX = 'pag:check_cache:'


class Command(BaseCommand):
    help = 'Comprueba que la cache responde y que se comparte entre procesos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--read',
            metavar='CLAVE',
            help=(
                'Uso interno: lee esa clave y la imprime. Es como se comprueba '
                'que la cache se ve desde otro proceso.'
            ),
        )

    def handle(self, *args, **options):
        if options['read']:
            self.stdout.write(str(cache.get(options['read'])))
            return None

        ok = True

        backend = self._report_backend()
        ok &= self._check_roundtrip()
        ok &= self._check_counter()
        ok &= self._check_expiry()
        shared = self._check_shared()

        self.stdout.write('')

        if not ok:
            self.stdout.write(self.style.ERROR(
                'La cache NO responde. Con ciertos backends esto no lanza '
                'excepcion, asi que el sitio sigue en pie pero los limites de '
                'tasa no se aplican.'
            ))

            return None

        if not shared:
            if 'locmem' not in backend.lower():
                self.stdout.write(self.style.ERROR(
                    'La cache responde pero NO se comparte entre procesos, y '
                    'con este backend eso no deberia pasar. Mira si cada '
                    'proceso esta leyendo una configuracion distinta.'
                ))
                return None

            self.stdout.write(self.style.WARNING(
                'LocMemCache: la cache funciona pero es POR PROCESO. Los '
                'limites de intentos son N veces mas laxos con N workers, y '
                'se reinician en cada despliegue. Para arreglarlo hace falta '
                'una cache compartida en CACHES (Redis, Memcached o '
                'DatabaseCache).'
            ))
            return None

        self.stdout.write(self.style.SUCCESS(
            'La cache funciona y se comparte entre procesos. Los contadores de '
            'tasa son de verdad.'
        ))

        return None

    # ------------------------------------------------------------------
    def _section(self, title):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(title))

    def _report_backend(self) -> str:
        """Que backend hay puesto. Es lo primero que hay que saber."""
        self._section('1. Backend')

        config = getattr(settings, 'CACHES', {}).get('default', {})
        backend = config.get('BACKEND', 'django.core.cache.backends.locmem.LocMemCache')

        self.stdout.write(f'   {backend}')

        if not config:
            self.stdout.write(
                '   Sin CACHES en los ajustes, Django usa LocMemCache, que es '
                'por proceso.'
            )
        elif config.get('LOCATION'):
            # Una URL de cache puede llevar contrasena: se enmascara.
            self.stdout.write(f'   servidor: {self._safe_location(config)}')

        return backend

    def _safe_location(self, config) -> str:
        """La URL del servidor sin la contrasena."""
        location = str(config.get('LOCATION', ''))

        if '@' not in location:
            return location

        scheme, _, rest = location.partition('://')
        _credentials, _, host = rest.rpartition('@')

        return f'{scheme}://***@{host}'

    def _check_roundtrip(self) -> bool:
        """
        Escribir y volver a leer, y cuanto cuesta cada cosa.

        Se miden **dos** tiempos, porque no son el mismo gasto y confundirlos
        lleva a conclusiones equivocadas:

        * **La primera vez** incluye abrir el TCP y negociar el TLS. Eso se
          paga una vez por proceso, no en cada peticion: django-redis mantiene
          un pool y las siguientes reutilizan la conexion. Lo paga cada worker
          nuevo, y en cPanel los workers se reciclan, asi que no es gratis --
          pero tampoco es lo que cuesta atender una peticion.

        * **Las siguientes** son lo que de verdad paga cada peticion con
          limite de tasa. Ese es el numero sobre el que hay que decidir.

        Con la conexion ya abierta, el tiempo de una operacion es basicamente
        la ida y vuelta por la red. Si sale alto, la causa suele ser la
        distancia fisica entre el servidor web y el Redis, y eso no se arregla
        configurando: se arregla acercandolos.
        """
        self._section('2. Ida y vuelta')

        key = f'{READ_PREFIX}{uuid.uuid4().hex}'
        value = {'probe': key}

        started = time.monotonic()
        cache.set(key, value, timeout=120)
        read = cache.get(key)
        cold = (time.monotonic() - started) * 1000

        if read != value:
            self.stdout.write(self.style.ERROR(
                f'   Se escribio y volvio {read!r}. Con IGNORE_EXCEPTIONS un '
                'servidor inalcanzable devuelve None sin lanzar: eso es lo '
                'que parece haber pasado.'
            ))
            return False

        self.stdout.write(self.style.SUCCESS(
            '   Escribe y lee correctamente.'
        ))

        # Ya con la conexion abierta: lo que cuesta de verdad cada peticion.
        samples = []

        for _ in range(5):
            started = time.monotonic()
            cache.set(key, value, timeout=120)
            cache.get(key)
            samples.append((time.monotonic() - started) * 1000)

        cache.delete(key)

        warm = sorted(samples)[len(samples) // 2]

        self.stdout.write(
            f'   Primera operacion: {cold:.0f} ms '
            '(incluye abrir conexion y TLS; se paga una vez por worker)'
        )
        self.stdout.write(
            f'   Ya conectado:      {warm:.0f} ms '
            '(esto es lo que paga cada peticion)'
        )

        self._comment_on_latency(cold, warm)

        return True

    def _comment_on_latency(self, cold, warm):
        """Que significan esos numeros, que es lo que no se ve solo."""
        if warm > 200:
            self.stdout.write(self.style.WARNING(
                '   Cada peticion con limite de tasa paga esos milisegundos, y '
                'con ATOMIC_REQUESTS los paga con una transaccion abierta. Con '
                'la conexion ya hecha, ese tiempo es casi todo distancia '
                'fisica: se arregla acercando la cache al servidor web.'
            ))
        elif warm > 50:
            self.stdout.write(
                '   Es un coste asumible para lo que se usa la cache, pero '
                'tenlo en cuenta antes de cachear nada en el camino critico.'
            )

        if cold > 800:
            self.stdout.write(self.style.WARNING(
                f'   Abrir la conexion cuesta {cold:.0f} ms. Un worker recien '
                'arrancado lo paga en su primera peticion, asi que si el '
                'hosting recicla workers a menudo se notara de vez en cuando.'
            ))

    def _check_counter(self) -> bool:
        """``incr``, que es como cuentan los limites de tasa."""
        self._section('3. Contador (incr)')

        key = f'{READ_PREFIX}counter:{uuid.uuid4().hex}'

        cache.set(key, 0, timeout=120)

        try:
            first = cache.incr(key)
            second = cache.incr(key)
        except Exception as error:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(
                f'   incr fallo: {type(error).__name__}: {error}'
            ))
            return False

        cache.delete(key)

        if (first, second) != (1, 2):
            self.stdout.write(self.style.ERROR(
                f'   Conto {first} y {second}, y deberia contar 1 y 2.'
            ))
            return False

        self.stdout.write(self.style.SUCCESS('   Cuenta bien: 1, 2.'))

        return True

    def _check_expiry(self) -> bool:
        """
        Que el TTL se respete.

        Sin caducidad, una ventana de limite no se cierra nunca y el cupo se
        agota para siempre.
        """
        self._section('4. Caducidad')

        key = f'{READ_PREFIX}ttl:{uuid.uuid4().hex}'

        cache.set(key, 'efimero', timeout=1)
        time.sleep(1.5)

        if cache.get(key) is not None:
            self.stdout.write(self.style.ERROR(
                '   La clave sigue ahi despues de caducar.'
            ))
            return False

        self.stdout.write(self.style.SUCCESS('   Las claves caducan.'))

        return True

    def _check_shared(self) -> bool:
        """
        La prueba que de verdad decide: leer desde OTRO proceso.

        Es la diferencia entre un limite compartido y uno por worker. Se lanza
        este mismo comando en un subproceso, que es un proceso distinto de
        verdad, igual que lo es cada worker del servidor web.
        """
        self._section('5. Compartida entre procesos')

        key = f'{READ_PREFIX}shared:{uuid.uuid4().hex}'
        value = uuid.uuid4().hex

        cache.set(key, value, timeout=120)

        argv = [
            sys.executable,
            os.path.join(str(settings.BASE_DIR), 'manage.py'),
            'check_cache',
            '--read', key,
        ]

        self.stdout.write('   Escrita aqui; leyendola desde otro proceso...')

        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(settings.BASE_DIR),
            )
        except Exception as error:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(
                f'   No se pudo lanzar el subproceso ({error}). Esta '
                'comprobacion queda sin hacer.'
            ))
            return True

        cache.delete(key)

        seen = (result.stdout or '').strip().splitlines()
        seen = seen[-1].strip() if seen else ''

        if seen != value:
            self.stdout.write(self.style.ERROR(
                f'   El otro proceso NO la vio (leyo {seen!r}).'
            ))
            return False

        self.stdout.write(self.style.SUCCESS(
            '   El otro proceso la ve. La cache es compartida.'
        ))

        return True

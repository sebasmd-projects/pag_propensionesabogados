# apps/common/utils/management/commands/check_media.py
"""
Diagnostico del almacenamiento de media.

``FileField`` guarda la ruta **relativa** a la raiz de su almacen. Si la
variable apunta a un sitio y los archivos estan en otro, no se pierde nada,
pero Django deja de encontrarlos: todas las descargas dan 404 y las subidas
nuevas van al directorio equivocado. Es un fallo silencioso --ni error ni
traza-- y por eso merece un comando que lo diga a la cara.

En pag hay **dos raices**, y las dos se miran:

* ``MEDIA_ROOT``: lo que sube el personal para el sitio publico (fotos del
  equipo, avisos modales) y lo que inserta CKEditor 5. El servidor web lo
  reparte directo, sin pasar por Django.
* ``PRIVATE_MEDIA_ROOT``: los PDF del paz y salvo. **Fuera** de ``MEDIA_ROOT``
  y sin publicar; solo salen por las vistas del gestor con permiso.

Que carpeta puede servirse y cual no lo decide ``utils/media_audit.py``, que es
lo mismo que lee ``check_security``. Ver ese fichero para la lista de lo que
sube quien.
"""

import os
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from ...media_audit import (MEDIA_HTACCESS, PUBLICLY_SERVABLE_MEDIA,
                            is_inside, upload_fields)
from ...outbound import InsecureUrlScheme, require_http_url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Un 301/302 no es un «se entrega»: se ve tal cual."""

    def redirect_request(self, *args, **kwargs):
        return None


class Command(BaseCommand):
    help = (
        'Comprueba que MEDIA_ROOT y PRIVATE_MEDIA_ROOT apuntan a donde estan '
        'los archivos, que los referenciados desde la base de datos existen '
        'en disco, y que lo privado no queda servido por el servidor web.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--sample', type=int, default=25,
            help='Cuantos archivos por campo se comprueban en disco.'
        )
        parser.add_argument(
            '--find', metavar='RUTA', default='',
            help=(
                'Si falta algun archivo, lo busca por nombre bajo esta ruta '
                'y dice donde esta. Util despues de mover una raiz.'
            )
        )
        parser.add_argument(
            '--http', action='store_true',
            help=(
                'Comprueba de verdad, por HTTP contra PUBLIC_BASE_URL, que un '
                'archivo privado NO se entrega bajo MEDIA_URL.'
            )
        )

    def handle(self, *args, **options):
        self.problems = 0

        self._roots()
        missing = self._referenced(options['sample'])
        self._find_missing(missing, options['find'])
        self._exposure()

        if options['http']:
            self._probe_http()

        self.stdout.write('')

        if self.problems:
            self.stdout.write(self.style.ERROR(f'{self.problems} problema(s).'))
        else:
            self.stdout.write(self.style.SUCCESS('Sin problemas.'))

    # ------------------------------------------------------------------
    def _bad(self, message):
        self.problems += 1
        self.stdout.write(self.style.ERROR(message))

    def _roots(self):
        media = str(settings.MEDIA_ROOT)
        private = str(getattr(settings, 'PRIVATE_MEDIA_ROOT', ''))

        self.stdout.write(self.style.MIGRATE_HEADING('MEDIA_ROOT (publico)'))
        self.stdout.write(f'  {media}')
        self.stdout.write(f'  MEDIA_URL: {settings.MEDIA_URL}')

        if not os.path.isdir(media):
            self._bad(
                '  El directorio NO existe. Django no encontrara ningun '
                'archivo y las subidas nuevas fallaran o crearan el arbol en '
                'el sitio equivocado.'
            )
        else:
            entries = sorted(
                name for name in os.listdir(media) if not name.startswith('.')
            )
            self.stdout.write(f'  Contenido: {", ".join(entries[:30]) or "(vacio)"}')

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'PRIVATE_MEDIA_ROOT (paz y salvo)'
        ))
        self.stdout.write(f'  {private}')

        if not private:
            self._bad('  No esta definido.')
        else:
            if is_inside(private, media) or is_inside(media, private):
                self._bad(
                    '  Esta dentro de MEDIA_ROOT (o lo contiene): el servidor '
                    'web repartiria los PDF del paz y salvo sin pasar por '
                    'Django.'
                )

            if 'public_html' in Path(private).parts:
                self._bad(
                    '  Cuelga de public_html: el servidor web puede '
                    'repartirlo. Debe quedar fuera del arbol que se publica.'
                )

            if not os.path.isdir(private):
                self.stdout.write(self.style.WARNING(
                    '  Todavia no existe (se crea con el primer paz y '
                    'salvo). Comprueba que el usuario de la aplicacion pueda '
                    'crearlo.'
                ))

        self.stdout.write('')

    def _referenced(self, sample):
        """Archivos referenciados desde la base de datos que no estan."""
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Archivos referenciados en la base de datos'
        ))

        total_missing = 0
        total_checked = 0
        missing_all = []

        for row in upload_fields():
            model, field, label = row['model'], row['field'], row['label']
            name = field.name
            root = row['root']
            mark = ' [privado]' if row['private'] else ''

            if root is None:
                self.stdout.write(self.style.WARNING(
                    f'  {label}: no se sabe donde guarda; sin comprobar'
                ))
                continue

            try:
                values = list(
                    model.objects
                    .exclude(**{name: ''})
                    .exclude(**{f'{name}__isnull': True})
                    .values_list(name, flat=True)[:sample]
                )
            except Exception as error:  # noqa: BLE001
                self.stdout.write(f'  {label}: no se pudo consultar ({error})')
                continue

            if not values:
                continue

            absent = [
                str(value) for value in values
                if not os.path.isfile(os.path.join(str(root), str(value)))
            ]

            total_checked += len(values)
            total_missing += len(absent)
            missing_all.extend(absent)

            if absent:
                self._bad(
                    f'  {label}{mark}: {len(absent)}/{len(values)} NO estan '
                    'en disco'
                )
                for value in absent[:3]:
                    self.stdout.write(f'      falta: {value}')
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'  {label}{mark}: {len(values)}/{len(values)} correctos'
                ))

        self.stdout.write('')

        if total_missing:
            self.stdout.write(
                '  Los archivos no se han perdido: lo mas probable es que la '
                'raiz (MEDIA_ROOT o PRIVATE_MEDIA_ROOT) no apunte a donde '
                'estan. Corrige la variable, o mueve los archivos, pero que '
                'ambos coincidan.'
            )
        elif total_checked:
            self.stdout.write(self.style.SUCCESS(
                f'Los {total_checked} archivos comprobados estan donde su '
                'raiz dice.'
            ))
        else:
            self.stdout.write('  (ningun campo tiene archivos todavia)')

        return missing_all

    def _find_missing(self, missing_all, search_root):
        if not missing_all:
            return

        self.stdout.write('')

        if not search_root:
            self.stdout.write(
                '  Para saber donde estan, repite con:  --find /home/propensi'
            )
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Buscando los archivos que faltan bajo {search_root}'
        ))

        index = {}

        for base, _dirs, names in os.walk(search_root):
            for name in names:
                index.setdefault(name, []).append(os.path.join(base, name))

        for relative in missing_all:
            found = index.get(os.path.basename(relative), [])

            if found:
                self.stdout.write(self.style.WARNING(f'  {relative}'))
                for path in found[:3]:
                    self.stdout.write(f'      esta en: {path}')
            else:
                self.stdout.write(self.style.ERROR(
                    f'  {relative}: no aparece por ningun lado. '
                    'Probablemente se borro; el registro sigue apuntando a un '
                    'archivo inexistente.'
                ))

    # ------------------------------------------------------------------
    def _exposure(self):
        """Que carpetas de MEDIA_ROOT reparte el servidor web, y por que."""
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Lo que reparte el servidor web bajo MEDIA_ROOT'
        ))

        htaccess = Path(str(settings.MEDIA_ROOT)) / '.htaccess'
        deploy = Path(settings.BASE_DIR) / MEDIA_HTACCESS

        for row in upload_fields():
            if row['private']:
                continue

            prefix = row['prefix']

            if prefix in PUBLICLY_SERVABLE_MEDIA:
                self.stdout.write(
                    f'  {prefix}/ se sirve directo: '
                    f'{PUBLICLY_SERVABLE_MEDIA[prefix]}'
                )
            else:
                self._bad(
                    f'  {row["label"]} escribe en {prefix or "(raiz)"}/ bajo '
                    'MEDIA_ROOT y no esta declarado como servible en '
                    'utils/media_audit.py: o se declara con su razon, o se '
                    'mueve a PRIVATE_MEDIA_ROOT.'
                )

        self.stdout.write(
            '  (raiz de MEDIA_ROOT: lo que sube CKEditor 5, solo imagenes '
            'del personal)'
        )

        if getattr(settings, 'CKEDITOR_5_ALLOW_ALL_FILE_TYPES', False):
            self._bad(
                '  CKEDITOR_5_ALLOW_ALL_FILE_TYPES esta activo: CKEditor '
                'aceptaria cualquier tipo de fichero en la raiz de MEDIA_ROOT.'
            )

        if htaccess.is_file():
            self.stdout.write(self.style.SUCCESS(
                f'  Hay un .htaccess en MEDIA_ROOT: {htaccess}'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'  No hay .htaccess en MEDIA_ROOT ({htaccess}). No hace falta '
                'para ocultar carpetas sensibles --no hay ninguna bajo '
                'MEDIA_ROOT-- pero conviene uno que apague la ejecucion de '
                'scripts y los listados (ver docs/SEGURIDAD.md, «Checklist '
                'antes de desplegar»).'
            ))

        if not deploy.is_file():
            self.stdout.write(
                f'  ({MEDIA_HTACCESS} no existe en el repositorio.)'
            )

    def _probe_http(self):
        """Un archivo privado, pedido por MEDIA_URL, no se entrega."""
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Comprobacion real por HTTP'
        ))

        sample = None

        for row in upload_fields():
            if not row['private'] or row['root'] is None:
                continue

            value = (
                row['model'].objects
                .exclude(**{row['field'].name: ''})
                .values_list(row['field'].name, flat=True).first()
            )

            if value:
                sample = str(value)
                break

        base = str(getattr(settings, 'PUBLIC_BASE_URL', '') or '').rstrip('/')

        if not sample:
            self.stdout.write(
                '  No hay ningun archivo privado en la base de datos con el '
                'que probar.'
            )
            return

        # El nombre relativo del archivo, colgado de MEDIA_URL: donde estaria
        # si el servidor web publicara la raiz privada por error.
        url = f'{base}{settings.MEDIA_URL}{sample}'
        self.stdout.write(f'  {url}')

        try:
            require_http_url(url)
        except InsecureUrlScheme as error:
            self._bad(f'  {error}')
            return

        opener = urllib.request.build_opener(_NoRedirect)
        request = urllib.request.Request(url, method='HEAD')

        try:
            with opener.open(request, timeout=15) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        except (urllib.error.URLError, OSError) as error:
            self.stdout.write(self.style.WARNING(
                f'  No se pudo comprobar: {error}'
            ))
            return

        if status in (301, 302, 403, 404):
            self.stdout.write(self.style.SUCCESS(
                f'  {status}: el servidor web NO entrega el archivo. Correcto.'
            ))
        else:
            self._bad(
                f'  {status}: el servidor web SIGUE ENTREGANDO el archivo '
                'privado sin pasar por Django.'
            )

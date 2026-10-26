"""
La cache de `settings.py`: LocMemCache sin `REDIS_URL`, django-redis con ella.

Lo que se protege aqui no es el formato del diccionario sino tres cosas que ya
mordieron en gea (el otro proyecto que usa el mismo Redis):

* **El prefijo es un ajuste de modulo**, no solo una clave de `CACHES`. Leido
  solo dentro del diccionario, `settings.REDIS_KEY_PREFIX` no existe y cada
  comprobacion cae en su propio defecto.
* **Las sesiones no se mueven a la cache.** Un Redis caido no puede cerrar la
  sesion de nadie.
* **Con django-redis y `IGNORE_EXCEPTIONS`, una cache caida no lanza: devuelve
  `None`.** `RateLimit` lo detecta por lo que devuelve `incr`; la ultima clase
  lo prueba contra un django-redis real apuntando a un puerto sin nadie.

`settings.py` se ejecuta aparte, con un entorno controlado, sin tocar el
modulo de ajustes en uso.
"""

import importlib.util
import os
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.http import HttpRequest
from django.test import SimpleTestCase, override_settings

from apps.common.utils.throttling import RateLimit

SETTINGS = Path(__file__).resolve().parent.parent / 'settings.py'
URL = 'rediss://pag:secreto@redis.example.invalid:6380/2'


def load_settings(**environ):
    """
    Ejecuta `settings.py` con ese entorno y devuelve el modulo resultante.

    Parte del entorno actual (que ya trae lo obligatorio) y quita
    `REDIS_*` antes de aplicar lo pedido, para que el `.env` de quien ejecuta
    las pruebas no decida el resultado. `load_dotenv` se anula por lo mismo:
    rellenaria `REDIS_URL` desde el fichero.
    """
    base = {
        key: value for key, value in os.environ.items()
        if not key.startswith('REDIS_')
    }
    base.update(environ)

    spec = importlib.util.spec_from_file_location(
        'settings_under_test', SETTINGS)
    module = importlib.util.module_from_spec(spec)

    with mock.patch.dict(os.environ, base, clear=True), \
            mock.patch('dotenv.load_dotenv', lambda *a, **k: False):
        spec.loader.exec_module(module)

    return module


class CacheBranchTests(SimpleTestCase):

    def test_without_redis_url_django_keeps_its_default_cache(self):
        module = load_settings()

        self.assertEqual(module.REDIS_URL, '')
        self.assertFalse(
            hasattr(module, 'CACHES'),
            'sin REDIS_URL no se define CACHES: Django usa LocMemCache')

    def test_a_blank_redis_url_counts_as_absent(self):
        module = load_settings(REDIS_URL='   ')

        self.assertEqual(module.REDIS_URL, '')
        self.assertFalse(hasattr(module, 'CACHES'))

    def test_with_redis_url_it_uses_django_redis_that_ignores_outages(self):
        module = load_settings(REDIS_URL=URL)
        config = module.CACHES['default']

        self.assertEqual(config['BACKEND'], 'django_redis.cache.RedisCache')
        self.assertEqual(config['LOCATION'], URL)
        self.assertIs(config['OPTIONS']['IGNORE_EXCEPTIONS'], True)
        self.assertTrue(module.DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS)

    def test_the_timeouts_default_to_three_seconds_and_can_be_set(self):
        default = load_settings(REDIS_URL=URL).CACHES['default']['OPTIONS']
        custom = load_settings(
            REDIS_URL=URL, REDIS_CONNECT_TIMEOUT='1', REDIS_TIMEOUT='2',
        ).CACHES['default']['OPTIONS']

        self.assertEqual(default['SOCKET_CONNECT_TIMEOUT'], 3)
        self.assertEqual(default['SOCKET_TIMEOUT'], 3)
        self.assertEqual(custom['SOCKET_CONNECT_TIMEOUT'], 1)
        self.assertEqual(custom['SOCKET_TIMEOUT'], 2)

    def test_sessions_do_not_move_to_the_cache(self):
        module = load_settings(REDIS_URL=URL)

        engine = getattr(
            module, 'SESSION_ENGINE', 'django.contrib.sessions.backends.db')

        self.assertNotIn('cache', engine)


class KeyPrefixTests(SimpleTestCase):

    def test_the_prefix_defaults_to_pag_and_is_a_module_setting(self):
        """El prefijo de gea es `gea`: el de este sitio no puede coincidir."""
        for module in (load_settings(), load_settings(REDIS_URL=URL)):
            self.assertEqual(module.REDIS_KEY_PREFIX, 'pag')

        self.assertEqual(
            load_settings(REDIS_URL=URL).CACHES['default']['KEY_PREFIX'],
            'pag')

    def test_the_prefix_comes_from_the_environment_in_both_places(self):
        module = load_settings(REDIS_URL=URL, REDIS_KEY_PREFIX='otro')

        self.assertEqual(module.REDIS_KEY_PREFIX, 'otro')
        self.assertEqual(module.CACHES['default']['KEY_PREFIX'], 'otro')

    def test_an_empty_prefix_falls_back_instead_of_sharing_keys(self):
        """Sin prefijo las claves de dos sitios en el mismo Redis chocarian."""
        module = load_settings(REDIS_URL=URL, REDIS_KEY_PREFIX='')

        self.assertEqual(module.REDIS_KEY_PREFIX, 'pag')
        self.assertEqual(module.CACHES['default']['KEY_PREFIX'], 'pag')


#: Un puerto en el que no escucha nadie: la conexion se rechaza al instante.
DEAD_REDIS = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:1/0',
        'KEY_PREFIX': 'pag',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
            'SOCKET_CONNECT_TIMEOUT': 1,
            'SOCKET_TIMEOUT': 1,
        },
    }
}


def request_from(ip='203.0.113.50'):
    request = HttpRequest()
    request.META['REMOTE_ADDR'] = ip
    return request


@override_settings(CACHES=DEAD_REDIS)
class RateLimitWithADeadRedisTests(SimpleTestCase):
    """
    El fallo que `IGNORE_EXCEPTIONS` esconde, contra django-redis de verdad
    (no contra un doble): la cache no lanza, devuelve `None`.
    """

    def test_the_trap_is_real_a_dead_redis_does_not_raise(self):
        """Si esta prueba falla, el detector de `RateLimit` ya no hace falta."""
        self.assertIsNone(cache.get('lo-que-sea'))
        self.assertIsNone(cache.add('contador', 0, timeout=5))
        self.assertIsNone(cache.incr('contador'))

        # Lo que haria un contador que lee la cache a mano (invariante de gea):
        self.assertEqual(cache.get('contador') or 0, 0)

    def test_the_limit_fails_closed_by_default(self):
        limit = RateLimit('prueba_cerrado', limit=5, window=60)

        self.assertFalse(limit.consume(request_from()))

    def test_fail_open_lets_the_request_through_only_when_asked(self):
        limit = RateLimit(
            'prueba_abierto', limit=5, window=60,
            fail_open=True, reason='prueba')

        self.assertTrue(limit.consume(request_from()))

    def test_fail_open_without_a_reason_is_refused(self):
        with self.assertRaises(ValueError):
            RateLimit('sin_razon', limit=5, window=60, fail_open=True)

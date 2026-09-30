# app_core/settings_test.py
"""
Settings OPCIONALES para ejecutar las pruebas rapido y aisladas.

El comando de siempre no cambia y sigue siendo el de referencia:

    manage.py test                                  # settings.py + tu base

Con estos settings las pruebas van contra SQLite en memoria, sin tocar la base
real ni pedir privilegios para crear ``test_...``:

    manage.py test --settings=app_core.settings_test
    manage.py test apps.common.utils --settings=app_core.settings_test

Sirve para una vuelta rapida mientras se trabaja. La suite completa se sigue
dando por buena en PostgreSQL (o el motor de produccion): SQLite no comprueba
lo que es propio del motor (tipos, bloqueos, ``ATOMIC_REQUESTS`` real).

Sigue haciendo falta un ``.env`` (copia ``docs/env.example``): ``settings.py``
lo lee y ``check_environment()`` protesta si falta algo. Lo unico que este
fichero deja de necesitar es la base de datos.

Lo que fija, y por que:

* ``ATOMIC_REQUESTS`` apagado: envuelve cada peticion en una transaccion y se
  lleva mal con las que abre el propio ``TestCase``.
* ``MEDIA_ROOT`` y ``PRIVATE_MEDIA_ROOT`` en directorios temporales: ninguna
  prueba escribe en los ficheros de verdad.
* Correo en memoria. **No** se cambian los hashers: hay pruebas que exigen
  ``argon2$`` y ``pbkdf2_sha256``, y un hasher de mentira las rompe.
* Independencia del ``.env``: con ``DJANGO_DEBUG=False`` el cliente de pruebas
  (http contra ``testserver``) se come un 301 a https en cada peticion.
* Sin escribir en ``stderr.log``: las pruebas que provocan errores a proposito
  no ensucian el fichero donde se buscan los fallos de verdad.
"""

import atexit
import shutil
import tempfile

from app_core.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

ATOMIC_REQUESTS = False

MEDIA_ROOT = tempfile.mkdtemp(prefix='pag_test_media_')
PRIVATE_MEDIA_ROOT = tempfile.mkdtemp(prefix='pag_test_private_')
# Que no quede rastro en el directorio temporal del sistema.
for _tmp in (MEDIA_ROOT, PRIVATE_MEDIA_ROOT):
    atexit.register(shutil.rmtree, _tmp, ignore_errors=True)

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# --- Independencia del .env -------------------------------------------------
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# La clave servidor a servidor: la API de Attlas y algunas pruebas la exigen.
# No es una credencial real; solo se rellena si el `.env` no la trae.
if not SERVER_KEY:  # noqa: F405
    SERVER_KEY = 'test-server-key-' + 'x' * 32

# Sin log a fichero (ver arriba).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {'class': 'logging.NullHandler'},
    },
    'root': {'handlers': ['null'], 'level': 'CRITICAL'},
}

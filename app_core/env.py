"""
Lectura del entorno: que falta en el `.env`, dicho por su nombre, y lecturas
tipadas que dicen de cual variable se quejan.

El problema
-----------
Varios `os.getenv()` de `settings.py` se pasaban directos a `int()` o a
`.split(',')` sin valor por defecto. Cuando falta una variable, el proyecto no
arranca --eso esta bien-- pero lo que se lee es esto:

    TypeError: int() argument must be a string ... not 'NoneType'
    AttributeError: 'NoneType' object has no attribute 'split'
    TypeError: argument of type 'NoneType' is not iterable

Ninguno nombra la variable. Hay que abrir `settings.py` por la linea de la
traza para averiguar de cual se trata, y repetir la operacion **una vez por
variable que falte**, porque el arranque muere en la primera.

Lo que hace esto
----------------
1. **`check_environment()`**: una sola pasada, antes de que `settings.py` lea
   nada. Si falta alguna variable de las que hoy rompen el arranque, levanta un
   `ImproperlyConfigured` que las nombra **todas juntas**, cada una con una
   linea de para que sirve, y la plantilla de `docs/env.example` al pie.
2. **`env_int()` / `env_list()`**: lecturas tipadas. Si el valor no es un
   entero, el error nombra la variable (`DB_PORT='abc'`), no un `ValueError`
   suelto. `env_list` parte por comas, recorta y descarta los huecos.

Cuatro decisiones que no son de gusto
-------------------------------------
1. **Solo es obligatorio lo que hoy ya rompe.** Esto no endurece el `.env`: una
   variable que hoy puede faltar sin que nada se caiga (`RECAPTCHA_*`,
   `DB_HOST`...) va en `OPTIONAL_WITHOUT_DEFAULT`, con el motivo escrito.
2. **Vacio cuenta como ausente**, salvo donde vacio significa algo. `DB_PORT=`
   rompe igual que no ponerlo (`int('')` tambien falla), y una clave de cifrado
   en blanco no es una clave. `COMMON_ATTACK_TERMS` vacio tampoco vale aqui:
   `'|'.join([''])` produce un patron que casa con TODAS las rutas. Las
   excepciones estan en `ALLOWED_EMPTY`.
3. **Hay variables que solo son obligatorias segun el motor de base de
   datos.** Con SQLite (`DB_ENGINE=django.db.backends.sqlite3`) `settings.py`
   no lee `DB_PORT` ni `DB_CONN_MAX_AGE`; exigirlas convertiria en error un
   `.env` de portatil que hoy funciona.
4. **Lo que se lee sin valor por defecto y aun asi puede faltar esta declarado
   aparte**, en `OPTIONAL_WITHOUT_DEFAULT`. No es decoracion: `test_env.py`
   recorre `settings.py`, y una variable nueva leida sin defecto que no este en
   ninguna lista falla la prueba. Asi la lista no se queda vieja sin que nadie
   lo note.
"""

import os

from django.core.exceptions import ImproperlyConfigured

# Donde esta la plantilla, para poder decirlo en el error.
ENV_EXAMPLE = 'docs/env.example'

SQLITE_ENGINE = 'django.db.backends.sqlite3'

# Obligatorias siempre: sin ellas hoy el proyecto no arranca (o no puede
# construir sus rutas). El texto es lo que se imprime al lado del nombre, asi
# que se escribe para quien acaba de ver el error y no conoce el proyecto.
REQUIRED = {
    'DJANGO_SECRET_KEY': (
        'Clave de firma de Django. Generala con '
        '`python -c "from django.core.management.utils import '
        'get_random_secret_key as k; print(k())"`.'
    ),
    'DJANGO_ADMIN_URL': (
        'Ruta donde cuelga el panel, con barra final y sin barra inicial '
        '(por ejemplo `panel-dev/`).'
    ),
    'DJANGO_ALLOWED_HOSTS': (
        'Dominios que sirve la aplicacion, separados por comas. Se lee en '
        'cualquier modo, DEBUG incluido.'
    ),
    'FIELD_ENCRYPTION_KEY': (
        'Clave Fernet con la que se cifra la PII en la base de datos. '
        'Generala con `python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"`. PERDERLA INUTILIZA LOS DATOS '
        'YA CIFRADOS.'
    ),
    'DB_ENGINE': (
        'Backend de base de datos, con su ruta completa: '
        '`django.db.backends.mysql`, `django.db.backends.postgresql` o '
        '`django.db.backends.sqlite3`.'
    ),
    'DJANGO_EMAIL_PORT': 'Puerto SMTP. Se convierte a entero.',
    'COMMON_ATTACK_TERMS': (
        'Terminos de la trampa anti-escaneo, separados por comas. No puede '
        'ir vacio: un patron sin terminos casa con todas las rutas.'
    ),
    'IP_BLOCKED_TIME_IN_MINUTES': (
        'Minutos del primer bloqueo por IP; se duplica en cada intento. Se '
        'convierte a entero.'
    ),
    'ATTLAS_TOKEN_TIMEOUT': (
        'Horas de validez del token de Attlas (settings lo pasa a segundos). '
        'Se convierte a entero.'
    ),
}

# Obligatorias solo si el motor no es SQLite: settings.py solo las lee en esa
# rama.
REQUIRED_UNLESS_SQLITE = {
    'DB_CONN_MAX_AGE': (
        'Segundos que se mantiene abierta la conexion a la base de datos. '
        'Se convierte a entero.'
    ),
    'DB_PORT': 'Puerto de la base de datos. Se convierte a entero.',
}

# Donde una cadena vacia es una respuesta y no un olvido.
ALLOWED_EMPTY = frozenset()

# Se leen sin valor por defecto y aun asi pueden faltar. Cada una con el motivo
# por el que su ausencia no rompe nada, que es lo que hay que comprobar antes
# de anadir una entrada aqui en vez de a REQUIRED.
OPTIONAL_WITHOUT_DEFAULT = {
    'DJANGO_DEBUG': (
        'Su ausencia significa DEBUG=False, que es el lado seguro: un olvido '
        'aqui deja el servidor en modo produccion, no al reves.'
    ),
    'DJANGO_LOG_FILE': (
        'Tiene alternativa en la propia linea (`or BASE_DIR / stderr.log`).'
    ),
    'DJANGO_EMAIL_USE_SSL': (
        'Se pasa por `bool()`, asi que ausente es False y el correo sale con '
        'TLS en vez de no arrancar.'
    ),
    'DJANGO_EMAIL_BACKEND': (
        'Ausente es None y Django usa su backend por defecto (SMTP): el '
        'arranque no se rompe, fallaria al mandar el primer correo.'
    ),
    'DJANGO_EMAIL_HOST': 'Solo se usa al mandar correo; ausente no rompe el arranque.',
    'DJANGO_EMAIL_HOST_USER': 'Solo se usa al mandar correo; ausente no rompe el arranque.',
    'DJANGO_EMAIL_HOST_PASSWORD': 'Solo se usa al mandar correo; ausente no rompe el arranque.',
    'DJANGO_EMAIL_DEFAULT_FROM_EMAIL': 'Solo se usa al mandar correo; ausente no rompe el arranque.',
    'DJANGO_STATIC_ROOT': (
        'Solo la usa `collectstatic`; ausente se lee como la cadena "None" '
        'y el servidor de desarrollo arranca igual.'
    ),
    'DJANGO_MEDIA_ROOT': (
        'Solo importa al guardar ficheros subidos; ausente se lee como la '
        'cadena "None" y el arranque no se rompe.'
    ),
    'DB_NAME': 'Con motor distinto de SQLite falla al conectar, no al arrancar.',
    'DB_USER': 'Con PostgreSQL puede ser None si se conecta por socket.',
    'DB_PASSWORD': 'Puede ser None si la base local no tiene contrasena.',
    'DB_HOST': 'None significa el socket local; es una conexion valida.',
    'DB_CHARSET': 'Solo lo usa el motor MySQL; ausente es None y se ignora.',
    'RECAPTCHA_PUBLIC_KEY': (
        'Ausente, django-recaptcha usa las claves de prueba de Google.'
    ),
    'RECAPTCHA_PRIVATE_KEY': (
        'Ausente, django-recaptcha usa las claves de prueba de Google.'
    ),
    'HONEYPOT_FIELD_NAME': (
        'Ausente, el campo trampa pierde su nombre pero el arranque no se '
        'rompe.'
    ),
    'CHAT_GPT_API_KEY': (
        'La traduccion automatica es opcional: sin clave, `translate()` '
        'devuelve el texto original en vez de fallar.'
    ),
    'SOCRATA_API_KEY': (
        'Solo la usan las consultas a datos abiertos; ausente no rompe el '
        'arranque.'
    ),
    'SOCRATA_API_KEY_SECRET': (
        'Solo la usan las consultas a datos abiertos; ausente no rompe el '
        'arranque.'
    ),
    'PRIVATE_MEDIA_ROOT': (
        'Tiene alternativa en la propia linea (`or BASE_DIR / private_media`).'
    ),
    'MIDDLEWARE_NOT_INCLUDE': (
        'Se declara y no lo consume nadie. `[None]` no rompe nada.'
    ),
}


def _is_set(name: str, value) -> bool:
    """¿Esta puesta? Vacia cuenta como ausente salvo en `ALLOWED_EMPTY`."""
    if value is None:
        return False

    if not value.strip():
        return name in ALLOWED_EMPTY

    return True


def expected_variables(environ=None) -> dict:
    """Las que tienen que estar, segun el motor de base de datos declarado."""
    environ = os.environ if environ is None else environ
    expected = dict(REQUIRED)

    if (environ.get('DB_ENGINE') or '').strip() != SQLITE_ENGINE:
        expected.update(REQUIRED_UNLESS_SQLITE)

    return expected


def missing_variables(environ=None) -> list:
    """Las que faltan, en el orden en que estan declaradas arriba."""
    environ = os.environ if environ is None else environ

    return [
        (name, reason)
        for name, reason in expected_variables(environ).items()
        if not _is_set(name, environ.get(name))
    ]


def format_missing(missing: list) -> str:
    """El texto del error: los nombres primero, y la plantilla al final."""
    cuantas = (
        'Falta 1 variable de entorno'
        if len(missing) == 1
        else f'Faltan {len(missing)} variables de entorno'
    )

    lineas = [
        f'{cuantas} y el proyecto no puede arrancar sin ellas.',
        '',
        'Se leen del fichero `.env` en la raiz del repositorio:',
        '',
    ]

    for name, reason in missing:
        lineas.append(f'  {name}')
        lineas.append(f'      {reason}')

    lineas += [
        '',
        f'La plantilla con todas, comentadas una a una, esta en {ENV_EXAMPLE}:',
        f'    cp {ENV_EXAMPLE} .env',
    ]

    return '\n'.join(lineas)


def check_environment(environ=None) -> None:
    """
    Levanta `ImproperlyConfigured` nombrando todo lo que falte.

    Se llama desde `settings.py` justo despues de `load_dotenv()`, antes de que
    nadie lea una variable: asi el error es la lista completa y no la primera
    linea que se tropieza.
    """
    missing = missing_variables(environ)

    if missing:
        raise ImproperlyConfigured(format_missing(missing))


_NO_DEFAULT = object()


def env_int(name: str, default=_NO_DEFAULT, environ=None) -> int:
    """
    Un entero del entorno. Si no lo es, el error dice cual variable es.

    Con `default`, ausente o vacia devuelve el defecto (que es lo que hacia
    `int(os.getenv(name, default))` salvo con la cadena vacia, que rompia).
    Sin `default`, ausente es un error con nombre.
    """
    environ = os.environ if environ is None else environ
    raw = environ.get(name)

    if raw is None or not raw.strip():
        if default is _NO_DEFAULT:
            raise ImproperlyConfigured(
                f'La variable de entorno {name} no esta puesta y hace falta '
                f'un numero entero. Plantilla: {ENV_EXAMPLE}.'
            )
        return int(default)

    try:
        return int(raw.strip())
    except ValueError:
        raise ImproperlyConfigured(
            f'La variable de entorno {name} debe ser un numero entero y vale '
            f'{raw!r}.'
        ) from None


def env_list(name: str, default=_NO_DEFAULT, environ=None) -> list:
    """
    Una lista del entorno, separada por comas.

    Recorta los espacios y descarta los huecos (`a,,b` -> `['a', 'b']`), asi
    una coma de mas no cuela un elemento vacio. Ausente o vacia devuelve una
    copia de `default`; sin `default`, es un error con nombre.
    """
    environ = os.environ if environ is None else environ
    raw = environ.get(name)
    items = [] if raw is None else [
        item.strip() for item in raw.split(',') if item.strip()
    ]

    if items:
        return items

    if default is _NO_DEFAULT:
        raise ImproperlyConfigured(
            f'La variable de entorno {name} no esta puesta o esta vacia y '
            f'hace falta una lista separada por comas. '
            f'Plantilla: {ENV_EXAMPLE}.'
        )

    return list(default)

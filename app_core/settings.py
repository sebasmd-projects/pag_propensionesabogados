import os
from datetime import timedelta
from pathlib import Path

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv
from import_export.formats.base_formats import CSV, HTML, JSON, TSV, XLS, XLSX

from app_core.db import engine_for
from app_core.env import check_environment, env_int, env_list

load_dotenv()

# Antes de leer nada: si faltan variables, el error las nombra todas juntas.
check_environment()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY')

if os.getenv('DJANGO_DEBUG') == 'True':
    DEBUG = True
else:
    DEBUG = False
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')


DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
]

THIRD_PARTY_APPS = [
    'axes',
    'corsheaders',
    'csp',
    'nested_admin',
    'rest_framework',
    'drf_spectacular',
    'auditlog',
    'django_recaptcha',
    'import_export',
    'parler',
    'rosetta',
    'django_ckeditor_5',
    'encrypted_model_fields',
    'formtools',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
]

OVERRIDDEN_THIRD_PARTY_APPS = [
    'two_factor',
]

CUSTOM_APPS = [
    'apps.common.core',
    'apps.common.utils',

    'apps.project.common.account',
    'apps.project.common.users',

    'apps.project.api.pqrs',
    'apps.project.api.financial_education',
    'apps.project.api.faq',
    'apps.project.api.platform.auth_platform',
    'apps.project.api.platform.insolvency_form',
    'apps.project.api.platform.calculator',
    'apps.project.case_manager',
]


ALL_CUSTOM_APPS = CUSTOM_APPS

INSTALLED_APPS = (
    THIRD_PARTY_APPS
    + ALL_CUSTOM_APPS
    + OVERRIDDEN_THIRD_PARTY_APPS
    + DJANGO_APPS
)

# import_export
IMPORT_EXPORT_FORMATS = [CSV, HTML, JSON, TSV, XLS, XLSX]

# Django Parler and i18n
LOCALE_PATHS = [
    app_path / 'locale' for app_path in [BASE_DIR / app.replace('.', '/') for app in ALL_CUSTOM_APPS]
]

LOCALE_PATHS.append(str(BASE_DIR / 'app_core' / 'locale'))

LANGUAGE_CODE = 'en'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True

LANGUAGES = [
    ('es', 'Español'),
    ('en', 'English')
]

PARLER_LANGUAGES = {
    None: (
        {'code': 'es', },
        {'code': 'en', },
    ),
    'default': {
        'fallbacks': ['en'],
        'hide_untranslated': False,
    }
}

UTILS_PATH = 'apps.common.utils'

ADMIN_URL = os.getenv('DJANGO_ADMIN_URL')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Arriba del todo, detras del de seguridad. Una peticion al `www` se va a
    # contestar con un 301 y nada mas, asi que no tiene sentido abrirle sesion,
    # resolverle el idioma, comprobarle el CSRF y anotarla en la auditoria
    # antes de mandarla a la direccion buena.
    'apps.common.utils.middleware.RedirectWWWMiddleware',
    # Solo pone la cabecera `Content-Security-Policy-Report-Only` en la
    # respuesta ya formada, asi que le da igual quien va detras. Despues del
    # `www`: un 301 no lleva politica.
    'csp.middleware.CSPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Justo detras del de autenticacion, que es de donde saca el usuario: es
    # quien pone `request.user.is_verified()` para las vistas que exigen
    # segundo factor.
    'django_otp.middleware.OTPMiddleware',
    # **Detras** de la autenticacion y del segundo factor, nunca antes: al
    # entrar mira `request.user` una sola vez para fijar el actor de todo lo
    # que se guarde durante la peticion. Puesto antes, `request.user` todavia
    # no existe y el rastro de auditoria queda sin usuario.
    'auditlog.middleware.AuditlogMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Los tres siguientes van juntos y despues de la autenticacion: los dos
    # ultimos miran `request.user` para eximir al personal interno. El primero
    # saca del acceso y del registro a quien ya tiene sesion; el segundo corta
    # rastreadores por politica y escaneres que se anuncian en el
    # `User-Agent`; el tercero aplica los bloqueos por IP y cuenta las rafagas
    # de 404. Los tres fallan abiertos.
    'apps.common.utils.middleware.RedirectAuthenticatedUserMiddleware',
    'apps.common.utils.middleware.BlockBadBotsMiddleware',
    'apps.common.utils.middleware.DetectSuspiciousRequestMiddleware',
    # El ultimo, como pide su documentacion: solo asi ve la respuesta ya
    # formada y puede convertir un intento fallido en un bloqueo.
    'axes.middleware.AxesMiddleware',
]

MIDDLEWARE_NOT_INCLUDE = [os.getenv('MIDDLEWARE_NOT_INCLUDE')]

ROOT_URLCONF = 'app_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                f'{UTILS_PATH}.context_processors.custom_processors',
                # La cabecera del sitio ensena el enlace al gestor solo a
                # quien puede entrar. El porque, en ese modulo.
                'apps.project.case_manager.context_processors.gestor_access'
            ],
        },
    },
]

WSGI_APPLICATION = 'app_core.wsgi.application'

ASGI_APPLICATION = 'app_core.asgi.application'

# El `.env` declara el motor de Django; con MySQL/MariaDB lo que se instala es
# `app_core/db/mysql`, que es el mismo con una sola diferencia: los UUID se
# siguen guardando como se guardaron. El porque esta en ese modulo.
DECLARED_DB_ENGINE = os.getenv('DB_ENGINE')

DB_ENGINE = engine_for(DECLARED_DB_ENGINE)

if DECLARED_DB_ENGINE != "django.db.backends.sqlite3":
    DATABASES = {
        'default': {
            'CONN_MAX_AGE': env_int('DB_CONN_MAX_AGE'),
            'ENGINE': DB_ENGINE,
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': env_int('DB_PORT'),
            'CHARSET': os.getenv('DB_CHARSET'),
            'ATOMIC_REQUESTS': True
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite',
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.UserModel'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
]

# `AxesStandaloneBackend` va **el primero**: es un guardian que se adelanta a
# los demas y corta si esa pareja (IP, usuario) ya gasto sus intentos. Detras
# quedan los dos de siempre, en el mismo orden que tenian.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
    f'{UTILS_PATH}.backend.EmailOrUsernameModelBackend',
]

# --- Acceso ---------------------------------------------------------------
# A donde se manda a quien no se ha identificado. Es el asistente de
# `account/urls.py`, que es el de `two_factor` con la entrada por codigo.
LOGIN_URL = 'account:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

#: Cuanto vive un codigo de seis cifras.
LOGIN_OTP_TTL_MINUTES = env_int('LOGIN_OTP_TTL_MINUTES', 15)

#: A quien escribir si a alguien le llega un codigo que no ha pedido.
OTP_CONTACT_EMAIL = os.getenv(
    'OTP_CONTACT_EMAIL', 'info@propensionesabogados.com')

#: A donde contestan los correos de la cuenta.
ACCOUNT_REPLY_TO = os.getenv(
    'ACCOUNT_REPLY_TO', 'info@propensionesabogados.com')

#: Cuanto vive el enlace para fijar una clave nueva, en segundos. Es el ajuste
#: que lee el generador de enlaces de Django. Su valor por defecto son tres
#: dias, demasiado para un enlace que da acceso a la cuenta.
PASSWORD_RESET_TIMEOUT = env_int('PASSWORD_RESET_TIMEOUT_MINUTES', 30) * 60

#: La direccion publica del sitio, para los enlaces que salen por correo. Nunca
#: se construyen con la cabecera `Host` de la peticion: la pone el cliente, y
#: un enlace de cambio de clave que apunte donde el atacante diga llegaria al
#: buzon de la victima desde nuestro propio servidor. `django.contrib.sites`
#: no esta instalado, asi que `get_current_site()` haria justo eso.
PUBLIC_BASE_URL = os.getenv(
    'PUBLIC_BASE_URL',
    'http://localhost:8000' if DEBUG else 'https://propensionesabogados.com',
)

#: Lo que sale como emisor en la aplicacion de codigos.
TWO_FACTOR_TOTP_DIGITS = 6
TWO_FACTOR_REMEMBER_COOKIE_AGE = None

# --- django-axes: freno al tanteo, sin dejar fuera al despacho ------------
# Los valores por defecto de `axes` son tres fallos y bloqueo **permanente**
# por IP. En un despacho que comparte salida a internet, eso es una persona
# tecleando mal su contrasena tres veces y todo el mundo fuera hasta que
# alguien entre a la base a mano. El porque de cada linea esta en
# `apps/common/utils/axes_hooks.py`.
AXES_LOCKOUT_PARAMETERS = [['ip_address', 'username']]
AXES_FAILURE_LIMIT = env_int('AXES_FAILURE_LIMIT', 6)
AXES_COOLOFF_TIME = timedelta(
    minutes=env_int('AXES_COOLOFF_MINUTES', 30)
)
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_CALLABLE = f'{UTILS_PATH}.axes_hooks.username'
AXES_CLIENT_IP_CALLABLE = f'{UTILS_PATH}.axes_hooks.client_ip'
AXES_WHITELIST_CALLABLE = f'{UTILS_PATH}.axes_hooks.is_lockout_exempt'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

SESSION_EXPIRE_AT_BROWSER_CLOSE = False

SESSION_COOKIE_AGE = 7200

# --- Cookies y subidas: explicito, no por defecto de Django ----------------
# Los tres primeros valen lo mismo que el defecto de Django; se escriben para
# que un cambio de version o un descuido no los mueva sin que nadie lo vea.
#: La cookie de sesion no la lee JavaScript: un XSS no puede robar la sesion.
SESSION_COOKIE_HTTPONLY = True
#: `Lax` y no `Strict`: `Strict` no manda la cookie al llegar desde un enlace
#: de otro sitio (el correo del codigo de acceso, el QR del paz y salvo) y esa
#: persona parecera no haber iniciado sesion. `Lax` frena igual el POST
#: cruzado, que es lo que importa.
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

#: Tope del cuerpo de una peticion SIN contar los ficheros (que van en partes
#: `multipart` y tienen su propio flujo). Lo que mas pesa hoy es la firma del
#: formulario de insolvencia de Attlas: un PNG de canvas en base64, medido en
#: 40-75 KB aun con un garabato denso a 3000 px de ancho. 5 MiB deja ~70 veces
#: de margen sin que un cuerpo desmedido se cargue entero en memoria (el
#: defecto de Django es 2,5 MiB). Los adjuntos del admin y la importacion son
#: ficheros en `multipart`: no cuentan aqui.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
#: Cuantos ficheros admite un solo envio. El gestor y el admin suben uno o dos
#: a la vez; el defecto de Django es 100, que abre cien descriptores antes de
#: que nadie valide nada.
DATA_UPLOAD_MAX_NUMBER_FILES = 20

# Clave servidor a servidor compartida por pag, fundacionattlas.org y gea:
# `X-Server-Key` de la API de Attlas, confianza en `X-Client-IP` y clave del
# emisor `propensiones` ante gea. Un solo nombre: `SERVER_KEY`.
# Transicion: si falta, se leen las variables viejas y un system check avisa
# (`utils.W002`). Retirar el fallback cuando produccion ya use `SERVER_KEY`.
SERVER_KEY = os.getenv('SERVER_KEY', '')
SERVER_KEY_LEGACY_VARS_IN_USE = []
#: Valor de la variable vieja de gea, solo mientras dure la transicion: hasta
#: hoy la clave de Attlas y la de gea podian ser distintas.
SERVER_KEY_LEGACY_GEA = ''
if not SERVER_KEY:
    for _legacy in ('ATTLAS_SERVER_KEY', 'GEA_ISSUER_KEY_PROPENSIONES'):
        _value = os.getenv(_legacy, '')
        if _value:
            SERVER_KEY_LEGACY_VARS_IN_USE.append(_legacy)
            SERVER_KEY = SERVER_KEY or _value
            if _legacy == 'GEA_ISSUER_KEY_PROPENSIONES':
                SERVER_KEY_LEGACY_GEA = _value
ATTLAS_CONSULTANT_EMAIL_DOMAINS = (
    'propensionesabogados.com', 'fundacionattlas.com', 'fundacionattlas.org',
)

ATTLAS_TOKEN_TIMEOUT = env_int('ATTLAS_TOKEN_TIMEOUT') * 60 * 60

# Lifetime in seconds for calculator-only tokens.
ATTLAS_LOOKUP_TOKEN_TIMEOUT = env_int("ATTLAS_LOOKUP_TOKEN_TIMEOUT", 30 * 60)

# Bootstrap llama `danger` a lo que Django llama `error`, y sin esto un
# mensaje de error se pinta con la clase `alert-error`, que no existe: el
# aviso sale sin color, o sea que el unico mensaje que importa es el que no se
# ve.
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

ROSETTA_SHOW_AT_ADMIN_PANEL = True

STATIC_URL = '/static/'

STATIC_ROOT = str(os.getenv('DJANGO_STATIC_ROOT'))

MEDIA_URL = '/media/'

MEDIA_ROOT = str(os.getenv('DJANGO_MEDIA_ROOT'))

STATICFILES_DIRS = [str(BASE_DIR / 'public' / 'staticfiles')]

# --- Paz y salvo certificado por gea ---------------------------------------
#: Base de la API de certificacion de gea, sin barra final (p. ej.
#: `https://geausa.propensionesabogados.com`). Vacia = no certifica: los paz y
#: salvo quedan PENDING hasta que se configure (y se corra
#: `certify_pending_paz_y_salvo`).
GEA_CERT_API_BASE_DEFAULT = 'https://geausa.propensionesabogados.com'
GEA_CERT_API_BASE = os.getenv('GEA_CERT_API_BASE', GEA_CERT_API_BASE_DEFAULT).strip().rstrip('/')
#: El slug con que gea conoce a este emisor.
GEA_ISSUER_SLUG = os.getenv('GEA_ISSUER_SLUG', 'propensiones').strip()
#: La clave ante gea es `SERVER_KEY` (la misma que en el `.env` de gea): es
#: una credencial de produccion, nunca va al codigo ni a los logs.
#: Segundos de espera (conexion, lectura) de cada llamada a gea.
GEA_CERT_TIMEOUT = (
    float(os.getenv('GEA_CERT_CONNECT_TIMEOUT', 10)),
    float(os.getenv('GEA_CERT_READ_TIMEOUT', 60)),
)
#: Intentos maximos de certificacion por documento antes de rendirse.
PAZ_Y_SALVO_MAX_ATTEMPTS = env_int('PAZ_Y_SALVO_MAX_ATTEMPTS', 5)
#: False (por defecto): certificar y revocar en linea, en el request, justo
#: tras confirmar la transaccion. True: en un hilo daemon (no fiable en
#: Passenger/cPanel, donde el proceso puede congelarse al responder).
PAZ_Y_SALVO_CERTIFY_ASYNC = os.getenv(
    'PAZ_Y_SALVO_CERTIFY_ASYNC', 'false').strip().lower() in ('1', 'true', 'yes')
#: Base publica de la URL que lleva el QR del paz y salvo. gea exige https.
PAZ_Y_SALVO_PUBLIC_BASE = os.getenv(
    'PAZ_Y_SALVO_PUBLIC_BASE', ''
).strip().rstrip('/') or PUBLIC_BASE_URL.rstrip('/')
#: Donde se guardan los PDF del paz y salvo. Va FUERA de `MEDIA_ROOT` a
#: proposito: el servidor web sirve `MEDIA_URL` sin pasar por Django, y el
#: original y la copia solo deben salir por sus vistas con permiso.
PRIVATE_MEDIA_ROOT = (
    os.getenv('PRIVATE_MEDIA_ROOT') or str(BASE_DIR / 'private_media'))

if bool(os.getenv('DJANGO_EMAIL_USE_SSL')):
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
else:
    EMAIL_USE_SSL = False
    EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = os.getenv('DJANGO_EMAIL_DEFAULT_FROM_EMAIL')
EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND')
EMAIL_HOST = os.getenv('DJANGO_EMAIL_HOST')
EMAIL_HOST_PASSWORD = os.getenv('DJANGO_EMAIL_HOST_PASSWORD')
EMAIL_HOST_USER = os.getenv('DJANGO_EMAIL_HOST_USER')
EMAIL_PORT = env_int('DJANGO_EMAIL_PORT')


# CKEditor
customColorPalette = [
    {
        'color': 'hsl(4, 90%, 58%)',
        'label': 'Red'
    },
    {
        'color': 'hsl(340, 82%, 52%)',
        'label': 'Pink'
    },
    {
        'color': 'hsl(291, 64%, 42%)',
        'label': 'Purple'
    },
    {
        'color': 'hsl(262, 52%, 47%)',
        'label': 'Deep Purple'
    },
    {
        'color': 'hsl(231, 48%, 48%)',
        'label': 'Indigo'
    },
    {
        'color': 'hsl(207, 90%, 54%)',
        'label': 'Blue'
    },
]

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': [
            'heading', '|',
            'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'removeFormat', '|',
            'bold', 'italic', 'underline', 'strikethrough', 'code', 'link', 'subscript', 'superscript', '|',
            'bulletedList', 'numberedList', 'todoList', '|',
            'insertImage', 'mediaEmbed', '|',
            'outdent', 'indent', '|',
            'blockQuote', 'insertTable', '|',
            'sourceEditing',
        ],
    },
    'list': {
        'properties': {
            'styles': 'true',
            'startIndex': 'true',
            'reversed': 'true',
        }
    }
}

CKEDITOR_5_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


# reCaptchav3
RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY')

# chatgpt
CHAT_GPT_API_KEY = os.getenv('CHAT_GPT_API_KEY')

# Socrata
SOCRATA_API_KEY = os.getenv('SOCRATA_API_KEY')
SOCRATA_API_KEY_SECRET = os.getenv('SOCRATA_API_KEY_SECRET')

HONEYPOT_FIELD_NAME = os.getenv('HONEYPOT_FIELD_NAME')

IP_BLOCKED_TIME_IN_MINUTES = env_int('IP_BLOCKED_TIME_IN_MINUTES')

# Django Rest Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Propensiones Abogados API',
    'DESCRIPTION': 'API',
    'VERSION': 'v1',
    'CONTACT': {'email': 'support@propensionesabogados.com'},
    'TERMS_OF_SERVICE': 'https://fundacionattlas.org/es/documentos/legales/terminos-y-condiciones',
    # Un solo nombre para el conjunto de opciones de tipo de solicitud de PQRS
    # (se repite en varios campos y drf-spectacular avisaba del choque).
    'ENUM_NAME_OVERRIDES': {
        'RequestTypeEnum': 'apps.project.api.pqrs.models.PQRSModel.RequestTypeChoicesEN',
    },
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated', 'rest_framework.permissions.IsAdminUser'],

    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'displayOperationId': False,
        'defaultModelsExpandDepth': 1,
        'defaultModelExpandDepth': 1,
        'docExpansion': 'list',
    },

    # Swagger UI y ReDoc se cargan desde jsDelivr. La biblioteca trae `@latest`
    # por defecto, o sea codigo que cambia sin que nadie lo revise y sin
    # `integrity`: aqui la version esta fijada y las plantillas de
    # `templates/drf_spectacular/` llevan el hash de esa version exacta. Al
    # subir de version, sacar los hashes de nuevo (ver `utils/tests/test_sri.py`).
    'SWAGGER_UI_DIST': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.33.0',
    'SWAGGER_UI_FAVICON_HREF': (
        'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.33.0/favicon-32x32.png'
    ),
    'REDOC_DIST': 'https://cdn.jsdelivr.net/npm/redoc@2.5.4',

    'SORT_OPERATIONS': True,
    'SORT_OPERATION_PARAMETERS': True,
}

# --- CORS: origenes enumerados, sin comodin de subdominio -------------------
# Un `*.propensionesabogados.com` deja hablar con la API a cualquier subdominio,
# presente o futuro: basta uno abandonado apuntando a un servicio de terceros.
# Se enumeran los sitios que de verdad llaman a la API desde el navegador,
# con y sin `www`. Cambiable con `CORS_ALLOWED_ORIGINS` (lista separada por
# comas; vacia o ausente = esta lista).
CORS_ALLOWED_ORIGINS_DEFAULT = [
    'https://geausa.propensionesabogados.com',
    'https://www.geausa.propensionesabogados.com',
    'https://fundacionattlas.com',
    'https://www.fundacionattlas.com',
    'https://fundacionattlas.org',
    'https://www.fundacionattlas.org',
]

if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://0.0.0.0:3000',
    ]
else:
    CORS_ALLOWED_ORIGINS = env_list(
        'CORS_ALLOWED_ORIGINS', CORS_ALLOWED_ORIGINS_DEFAULT)

# --- CSP en modo solo informe ----------------------------------------------
# `Content-Security-Policy-Report-Only`: el navegador NO bloquea nada, solo
# avisa a `CSP_REPORT_PATH` de lo que bloquearia. Es para ver que romperia
# antes de hacerla efectiva; el siguiente paso esta en `docs/SEGURIDAD.md`.
#
# Los origenes salen de recorrer las plantillas: Google Fonts (`base.html`),
# DataTables y pdfmake (gestor), reCAPTCHA (formulario de contacto), el icono
# de Trace en la cabecera y Swagger/ReDoc (jsdelivr, solo el personal).
# Bootstrap, iconos, Swiper y AOS son locales (`public/staticfiles`).
#
# `script-src` NO lleva `'unsafe-inline'` a proposito: hay scripts en linea en
# las plantillas y se quiere que salgan en los informes. `style-src` si, porque
# hay atributos `style=` por todas partes y no admiten nonce.
CSP_REPORT_PATH = '/csp-report/'

_CSP_SELF = "'self'"
_CSP_RECAPTCHA_SCRIPTS = (
    'https://www.google.com/recaptcha/',
    'https://www.gstatic.com/recaptcha/',
)

CONTENT_SECURITY_POLICY_REPORT_ONLY = {
    'DIRECTIVES': {
        'default-src': [_CSP_SELF],
        'script-src': [
            _CSP_SELF,
            'https://cdn.jsdelivr.net',
            'https://cdn.datatables.net',
            *_CSP_RECAPTCHA_SCRIPTS,
        ],
        'style-src': [
            _CSP_SELF,
            "'unsafe-inline'",
            'https://fonts.googleapis.com',
            'https://cdn.datatables.net',
            'https://cdn.jsdelivr.net',
        ],
        'font-src': [
            _CSP_SELF,
            'data:',
            'https://fonts.gstatic.com',
            'https://cdn.jsdelivr.net',
        ],
        'img-src': [
            _CSP_SELF,
            'data:',
            'blob:',
            'https://tracecertificates.com',
            'https://cdn.jsdelivr.net',
        ],
        'connect-src': [_CSP_SELF, 'https://www.google.com/recaptcha/'],
        'frame-src': [
            'https://www.google.com/recaptcha/',
            'https://recaptcha.google.com/recaptcha/',
        ],
        'media-src': [_CSP_SELF],
        'object-src': [_CSP_SELF],
        'worker-src': [_CSP_SELF, 'blob:'],
        'base-uri': [_CSP_SELF],
        'form-action': [_CSP_SELF],
        'frame-ancestors': [_CSP_SELF],
        'report-uri': [CSP_REPORT_PATH],
    },
}


COMMON_ATTACK_TERMS = env_list('COMMON_ATTACK_TERMS')

# Detector de rafagas de 404 (`apps/common/utils/scanning.py`). Lo lee con
# `getattr(settings, ...)` y su propio defecto: sin estas lineas poner la
# variable en el `.env` no haria nada.
SCAN_404_THRESHOLD = env_int('SCAN_404_THRESHOLD', 20)
SCAN_404_WINDOW_SECONDS = env_int('SCAN_404_WINDOW_SECONDS', 300)

# Base GeoLite2 para el pais de una IP (`apps/common/utils/netintel.py`).
# Opcional: vacia, el campo se queda sin pais y todo lo demas sigue igual.
GEOIP_PATH = os.getenv('GEOIP_PATH', '')

# Fichero de log que rotan y leen `apps/common/utils/logs.py`
# (`manage.py rotate_logs` / `show_log`). Antes lo abria un
# `logging.basicConfig(filename='stderr.log')` relativo al directorio de
# trabajo; ahora es siempre `BASE_DIR/stderr.log` (o `DJANGO_LOG_FILE`).
LOG_FILE = Path(os.getenv('DJANGO_LOG_FILE') or (BASE_DIR / 'stderr.log'))

#: El handler es `WatchedFileHandler` a proposito, y no `FileHandler`. Rotar es
#: renombrar el fichero, y en Linux quien lo tiene abierto sigue escribiendo en
#: el renombrado: con `FileHandler`, tras `rotate_logs` todos los workers
#: seguirian escribiendo en `stderr_old_N.log` y el `stderr.log` nuevo no
#: llegaria a existir. `WatchedFileHandler` reabre el fichero al detectar el
#: cambio (ver `apps/common/utils/logs.py` y `tests/test_logs.py`). Formato y
#: nivel son los que ya tenia el `basicConfig`: WARNING en la raiz.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': str(LOG_FILE),
            'encoding': 'utf-8',
            'formatter': 'plain',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'WARNING',
    },
}

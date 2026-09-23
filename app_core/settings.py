import logging
import os
from datetime import timedelta
from pathlib import Path

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv
from import_export.formats.base_formats import CSV, HTML, JSON, TSV, XLS, XLSX

from app_core.db import engine_for

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

logging.basicConfig(
    filename='stderr.log', format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8'
)

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

if ',' in os.getenv('DJANGO_ALLOWED_HOSTS'):
    ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS').split(',')
else:
    ALLOWED_HOSTS = [os.getenv('DJANGO_ALLOWED_HOSTS')]


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
    # `axes` va el primero: envuelve al backend de siempre, y su orden en la
    # lista de aplicaciones es el que decide cuando se registran sus senales.
    'axes',
    'corsheaders',
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

    # El acceso: el asistente de `two_factor` sobre `formtools`, con los
    # dispositivos de `django_otp`. Los dos complementos que se instalan son
    # los unicos que hacen falta: `otp_totp` para la aplicacion de codigos y
    # `otp_static` para los codigos de respaldo que se apuntan en papel.
    'formtools',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
]

# `two_factor` se instala **detras** de las aplicaciones del proyecto y no
# aqui con el resto de terceros. El cargador de plantillas busca por el orden
# de `INSTALLED_APPS`, y las pantallas de acceso del proyecto --que viven en
# `apps/project/common/account/templates/two_factor/`-- tienen que ganarle a
# las de ejemplo que trae la biblioteca. Puesta con los demas terceros, lo que
# se servia era su pantalla gris con el aviso de «provide a template».
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
    'apps.project.api.platform.case_manager',
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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Justo detras del de autenticacion, que es de donde saca el usuario: es
    # quien pone `request.user.is_verified()` para las vistas que exigen
    # segundo factor.
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.common.utils.middleware.RedirectWWWMiddleware',
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
                'apps.project.api.platform.case_manager.context_processors.gestor_access'
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
            'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE')),
            'ENGINE': DB_ENGINE,
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': int(os.getenv('DB_PORT')),
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
LOGIN_OTP_TTL_MINUTES = int(os.getenv('LOGIN_OTP_TTL_MINUTES', 15))

#: A quien escribir si a alguien le llega un codigo que no ha pedido.
OTP_CONTACT_EMAIL = os.getenv(
    'OTP_CONTACT_EMAIL', 'info@propensionesabogados.com')

#: A donde contestan los correos de la cuenta.
ACCOUNT_REPLY_TO = os.getenv(
    'ACCOUNT_REPLY_TO', 'info@propensionesabogados.com')

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
AXES_FAILURE_LIMIT = int(os.getenv('AXES_FAILURE_LIMIT', 6))
AXES_COOLOFF_TIME = timedelta(
    minutes=int(os.getenv('AXES_COOLOFF_MINUTES', 30))
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

ATTLAS_TOKEN_TIMEOUT = int(os.getenv('ATTLAS_TOKEN_TIMEOUT'))*60*60

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
EMAIL_PORT = int(os.getenv('DJANGO_EMAIL_PORT'))


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

IP_BLOCKED_TIME_IN_MINUTES = int(os.getenv('IP_BLOCKED_TIME_IN_MINUTES'))

# Django Rest Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny'
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Propensiones Abogados API',
    'DESCRIPTION': 'API',
    'VERSION': 'v1',
    'CONTACT': {'email': 'support@propensionesabogados.com'},
    'TERMS_OF_SERVICE': 'https://fundacionattlas.org/es/documentos/legales/terminos-y-condiciones',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated', 'rest_framework.permissions.IsAdminUser'],

    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'displayOperationId': False,
        'defaultModelsExpandDepth': 1,
        'defaultModelExpandDepth': 1,
        'docExpansion': 'list',
    },

    'SORT_OPERATIONS': True,
    'SORT_OPERATION_PARAMETERS': True,
}

if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        'http://localhost:3000',
        'http://0.0.0.0:3000',
    ]
else:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r'^https://[A-Za-z0-9-]+\.propensionesabogados\.com$',
        r'^https://[A-Za-z0-9-]+\.fundacionattlas\.com$',
        r'^https://[A-Za-z0-9-]+\.fundacionattlas\.org$',
    ]


COMMON_ATTACK_TERMS = [
    term.strip() for term in os.getenv('COMMON_ATTACK_TERMS').split(',')
]

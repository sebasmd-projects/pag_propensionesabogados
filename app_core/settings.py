import logging
import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv
from import_export.formats.base_formats import CSV, HTML, JSON, TSV, XLS, XLSX

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
    'corsheaders',
    'nested_admin',
    'rest_framework',
    'drf_yasg',
    'auditlog',
    'honeypot',
    'django_recaptcha',
    'import_export',
    'parler',
    'rosetta',
    'django_ckeditor_5',
    'encrypted_model_fields',
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
]


ALL_CUSTOM_APPS = CUSTOM_APPS

if DEBUG:
    INSTALLED_APPS = THIRD_PARTY_APPS + ALL_CUSTOM_APPS + DJANGO_APPS
else:
    INSTALLED_APPS = THIRD_PARTY_APPS + ALL_CUSTOM_APPS + DJANGO_APPS

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
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.common.utils.middleware.RedirectWWWMiddleware',
    'apps.common.utils.middleware.DetectSuspiciousRequestMiddleware',
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
                f'{UTILS_PATH}.context_processors.custom_processors'
            ],
        },
    },
]

WSGI_APPLICATION = 'app_core.wsgi.application'

ASGI_APPLICATION = 'app_core.asgi.application'

DATABASES = {
    'default': {
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE')),
        'ENGINE': os.getenv('DB_ENGINE'),
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': int(os.getenv('DB_PORT')),
        'CHARSET': os.getenv('DB_CHARSET'),
        'ATOMIC_REQUESTS': True
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

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    f'{UTILS_PATH}.backend.EmailOrUsernameModelBackend',
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

SESSION_EXPIRE_AT_BROWSER_CLOSE = False

SESSION_COOKIE_AGE = 7200
ATTLAS_TOKEN_TIMEOUT = int(os.getenv('ATTLAS_TOKEN_TIMEOUT'))*60*60

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
    ]
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

from django.conf import settings
from django.core import checks


@checks.register(checks.Tags.security)
def check_server_key(app_configs, **kwargs):
    key = settings.SERVER_KEY
    problems = []
    if not settings.DEBUG and len(key) < 32:
        problems.append(checks.Error(
            'SERVER_KEY debe tener al menos 32 caracteres en producción.',
            id='utils.E001',
        ))
    elif settings.DEBUG and not key:
        problems.append(checks.Warning(
            'SERVER_KEY está vacía; la API de Attlas denegará el acceso.',
            id='utils.W001',
        ))
    legacy = getattr(settings, 'SERVER_KEY_LEGACY_VARS_IN_USE', None) or []
    if legacy:
        problems.append(checks.Warning(
            'Se usa la variable de entorno vieja %s; define SERVER_KEY '
            '(la misma clave en pag, gea y Vercel) y retira la vieja.'
            % ', '.join(legacy),
            id='utils.W002',
        ))
    return problems

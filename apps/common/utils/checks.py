from django.conf import settings
from django.core import checks


@checks.register(checks.Tags.security)
def check_attlas_server_key(app_configs, **kwargs):
    key = settings.ATTLAS_SERVER_KEY
    if not settings.DEBUG and len(key) < 32:
        return [checks.Error(
            'ATTLAS_SERVER_KEY debe tener al menos 32 caracteres en producción.',
            id='utils.E001',
        )]
    if settings.DEBUG and not key:
        return [checks.Warning(
            'ATTLAS_SERVER_KEY está vacía; la API de Attlas denegará el acceso.',
            id='utils.W001',
        )]
    return []

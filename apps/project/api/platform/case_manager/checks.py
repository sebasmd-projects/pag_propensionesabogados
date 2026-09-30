"""Avisos de configuracion del paz y salvo certificado por gea."""

from django.conf import settings
from django.core import checks


@checks.register(checks.Tags.compatibility)
def check_gea_certification(app_configs, **kwargs):
    problems = []

    if not settings.GEA_CERT_API_BASE:
        problems.append(checks.Warning(
            'GEA_CERT_API_BASE esta vacia: los paz y salvo se autorizan pero '
            'no se certifican (quedan PENDING).',
            id='case_manager.W001',
        ))
    if not settings.GEA_ISSUER_KEY:
        problems.append(checks.Warning(
            'GEA_ISSUER_KEY_PROPENSIONES esta vacia: no se puede certificar '
            'con gea.',
            id='case_manager.W002',
        ))
    if not settings.PAZ_Y_SALVO_PUBLIC_BASE.startswith('https://'):
        problems.append(checks.Warning(
            'PAZ_Y_SALVO_PUBLIC_BASE (o PUBLIC_BASE_URL) no es https: gea '
            'rechaza el QR.',
            id='case_manager.W003',
        ))

    return problems

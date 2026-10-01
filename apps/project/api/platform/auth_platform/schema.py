"""Extensiones de drf-spectacular para la autenticacion de la plataforma."""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class BearerTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    """Documenta BearerTokenAuthentication (y subclases) como Bearer HTTP."""

    target_class = (
        'apps.project.api.platform.auth_platform.authentication.'
        'BearerTokenAuthentication'
    )
    match_subclasses = True
    name = 'BearerTokenAuth'

    def get_security_definition(self, auto_schema):
        return {'type': 'http', 'scheme': 'bearer'}


class LookupOrPlatformTokenAuthenticationScheme(BearerTokenAuthenticationScheme):
    """Mismo esquema Bearer, con otro nombre para no chocar en los componentes."""

    target_class = (
        'apps.project.api.platform.auth_platform.authentication.'
        'LookupOrPlatformTokenAuthentication'
    )
    match_subclasses = True
    priority = 1
    name = 'LookupOrPlatformTokenAuth'

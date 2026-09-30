import hmac

from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def server_key_is_valid(request) -> bool:
    """Comprueba la clave del proxy en Django y DRF sin propagar errores."""
    try:
        expected = getattr(settings, 'SERVER_KEY', '')
        headers = getattr(request, 'headers', None) or {}
        meta = getattr(request, 'META', None) or {}
        provided = headers.get('X-Server-Key') or meta.get('HTTP_X_SERVER_KEY', '')
        return bool(expected) and hmac.compare_digest(
            provided.encode('utf-8'), expected.encode('utf-8')
        )
    except Exception:
        return False


class HasServerKey(BasePermission):
    """Restringe la API de Attlas al servidor proxy mediante una clave compartida."""

    message = 'Acceso denegado.'

    def has_permission(self, request, view):
        if not server_key_is_valid(request):
            # Evita que DRF convierta el rechazo en 401 en vistas con Bearer.
            raise PermissionDenied(self.message)
        return True

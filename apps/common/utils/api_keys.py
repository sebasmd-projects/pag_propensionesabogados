import hmac

from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class HasServerKey(BasePermission):
    """Restringe la API de Attlas al servidor proxy mediante una clave compartida."""

    message = 'Acceso denegado.'

    def has_permission(self, request, view):
        expected = settings.ATTLAS_SERVER_KEY
        provided = request.headers.get('X-Server-Key', '')
        if not expected or not hmac.compare_digest(
            provided.encode('utf-8'), expected.encode('utf-8')
        ):
            # Evita que DRF convierta el rechazo en 401 en vistas con Bearer.
            raise PermissionDenied(self.message)
        return True

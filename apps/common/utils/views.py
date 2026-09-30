import logging
import re
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from apps.common.utils.client_ip import get_client_ip
from .models import IPBlockedModel, WhiteListedIPModel

logger = logging.getLogger(__name__)

try:
    template_name = settings.ERROR_TEMPLATE
except AttributeError:
    template_name = 'errors_template.html'
except SystemExit:
    raise
except Exception as e:
    logger.error(f"An unexpected error occurred: {e}")
    template_name = 'errors_template.html'


SAFE_PATH_PREFIXES = [
    'static',
    'media',
    'favicon.ico',
    'api',
]

# OJO: estos se buscan con `search`, o sea en cualquier posicion de la ruta.
# Aqui solo van patrones que de verdad identifiquen una ruta inocua.
#
# Habia un `r'^(?!api/).*'` en esta lista. Con `search`, eso casa con **toda**
# ruta que no empiece por `api/` -- es decir, con casi todas -- asi que
# `is_safe_path` devolvia True para `/wp-admin/`, `/phpmyadmin/` y `/.env`.
# Consecuencia: el middleware se saltaba cada peticion sin mirar los bloqueos,
# y la propia vista trampa se iba por su primera linea sin crear ninguno. La
# mitigacion anti-escaneo llevaba sin hacer absolutamente nada.
SAFE_PATH_REGEXES = [
    # Las URL de verificacion de certificados llevan un UUID: son legitimas.
    r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
    r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
]

SAFE_PATH_EXTENSIONS = [
    '.css', '.js', '.png',
    '.jpg', '.jpeg', '.gif',
    '.svg', '.ico', '.woff',
    '.woff2', '.ttf', '.eot',
    '.otf', '.mp4', '.webm',
    '.ogg', '.mp3', '.wav'
]

_COMPILED_SAFE_REGEXES = [re.compile(r) for r in SAFE_PATH_REGEXES]


def _normalize_request_path(path: str) -> str:
    """
    Extrae y normaliza la parte de path sin query ni slash inicial.
    Ej: '/static/img/foo.png?x=1' -> 'static/img/foo.png'
    """
    if not path:
        return ''
    parsed = urlparse(path)
    p = parsed.path or ''
    # quitar slash inicial si existe
    if p.startswith('/'):
        p = p[1:]
    return p


def is_safe_path(path: str) -> bool:
    """
    True si la ruta debe considerarse 'safe' (recursos estáticos, extensiones, uuid, etc).
    Usar desde vistas y middleware.
    """
    if not path:
        return False

    p = _normalize_request_path(path)  # sin leading slash, sin query

    # 1) prefijos (ej. static/, media/, favicon.ico)
    for pref in SAFE_PATH_PREFIXES:
        # Segmento completo o coincidencia exacta. El `startswith(pref)` que
        # habia aqui daba por buena `/apiXYZ/` por culpa del prefijo `api`.
        if p == pref or p.startswith(pref + '/'):
            return True

    # 2) extensiones
    lower = p.lower()
    for ext in SAFE_PATH_EXTENSIONS:
        if lower.endswith(ext):
            return True

    # 3) regexes (buscar en todo el path)
    for cre in _COMPILED_SAFE_REGEXES:
        if cre.search(p):
            return True

    return False


def handler400(request, exception, *args, **argv):
    status = 400
    return render(
        request,
        template_name,
        status=status,
        context={
            'exception': str(exception),
            'title': _('Error 400'),
            'error': _('Bad Request'),
            'status': status,
            'error_favicon': 'https://propensionesabogados.com/static/assets/imgs/favicon/favicon.ico'
        }
    )


def handler403(request, exception, *args, **argv):
    status = 403
    return render(
        request,
        template_name,
        status=status,
        context={
            'exception': str(exception),
            'title': _('Error 403'),
            'error': _('Prohibited Request'),
            'status': status,
            'error_favicon': 'https://propensionesabogados.com/static/assets/imgs/favicon/favicon.ico'
        }
    )


def handler404(request, exception, *args, **argv):
    status = 404
    return render(
        request,
        template_name,
        status=status,
        context={
            'exception': str(exception),
            'title': _('Error 404'),
            'error': _('Page not found'),
            'status': status,
            'error_favicon': 'https://propensionesabogados.com/static/assets/imgs/favicon/favicon.ico'
        }
    )


def handler500(request, *args, **argv):
    status = 500
    return render(
        request,
        template_name,
        status=500,
        context={
            'title': _('Error 500'),
            'error': _('Server error'),
            'status': status,
            'error_favicon': 'https://propensionesabogados.com/static/assets/imgs/favicon/favicon.ico'
        }
    )


def set_language(request):
    lang_code = request.GET.get('lang', None)
    if lang_code and lang_code in dict(settings.LANGUAGES).keys():
        translation.activate(lang_code)
        response = redirect(request.META.get('HTTP_REFERER'))
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
        return response
    else:
        return redirect(request.META.get('HTTP_REFERER'))


class HttpRequestAttakView(View):
    time_in_minutes = timedelta(
        seconds=60 * settings.IP_BLOCKED_TIME_IN_MINUTES
    )

    def get(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)

        # Skip if IP is whitelisted
        if WhiteListedIPModel.objects.filter(current_ip=client_ip).exists():
            return redirect('/')

        resolver_match = getattr(request, 'resolver_match', None)
        view_name = resolver_match.view_name if resolver_match else None

        user_id = None
        if request.user and request.user.is_authenticated:
            user_id = str(request.user.id)

        query_params = dict(request.GET.lists())

        headers_info = {
            'accept_language': request.META.get('HTTP_ACCEPT_LANGUAGE'),
            'host': request.META.get('HTTP_HOST'),
        }

        # Prepare session data
        session_data = {
            'attempt_count': 1,
            'client_ip': client_ip,
            'paths': [request.path],
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'method': request.method,
            'referer': request.META.get('HTTP_REFERER'),
            'view_name': view_name,
            'user_id': user_id,
            'query_params': query_params,
            'headers': headers_info,
            'timestamp': timezone.now().isoformat(),
        }

        # Check if the IP is already blocked
        blocked_entry, created = IPBlockedModel.objects.get_or_create(
            current_ip=client_ip,
            defaults={
                'reason': IPBlockedModel.ReasonsChoices.SERVER_HTTP_REQUEST,
                'blocked_until': timezone.now() + self.time_in_minutes,
                'session_info': session_data
            }
        )

        if not created:
            # Update attempt count and paths
            attempt_count = blocked_entry.session_info.get('attempt_count', 0) + 1
            blocked_entry.session_info['attempt_count'] = attempt_count
            blocked_entry.session_info['paths'].append(request.path)
            blocked_entry.session_info['timestamp'] = timezone.now().isoformat()

            # Calculate block time
            if attempt_count > 2:
                block_time = self.time_in_minutes * 3600 * attempt_count
            else:
                block_time = self.time_in_minutes

            blocked_entry.blocked_until = timezone.now() + block_time
            blocked_entry.save()

        return redirect('/')

import logging

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.common.utils.models import IPBlockedModel

logger = logging.getLogger(__name__)


class RedirectWWWMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if host.startswith('www.'):
            non_www_host = host[4:]
            scheme = 'https' if request.is_secure() else 'http'
            non_www_url = f'{scheme}://{non_www_host}{request.get_full_path()}'
            return HttpResponsePermanentRedirect(non_www_url)
        response = self.get_response(request)
        return response


try:
    template_name = settings.ERROR_TEMPLATE
except AttributeError:
    template_name = 'errors_template.html'
except SystemExit:
    raise
except Exception as e:
    logger.error(f"An unexpected error occurred: {e}")
    template_name = 'errors_template.html'


class DetectSuspiciousRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip = request.META.get('REMOTE_ADDR')

        blocked_entry = IPBlockedModel.objects.filter(
            current_ip=client_ip,
            is_active=True,
            blocked_until__gte=timezone.now()
        ).first()

        if blocked_entry:
            logger.warning(
                f"Blocked IP {client_ip} attempted access. Returning 403.")
            return render(
                request,
                template_name,
                status=403,
                context={
                    'exception': _('This IP is temporarily blocked due to suspicious activity.'),
                    'title': _('Error 403'),
                    'error': _('Access denied due to suspicious activity.'),
                    'status': 403,
                    'attempt_count': blocked_entry.session_info.get('attempt_count', 1),
                }
            )

        response = self.get_response(request)

        if response.status_code > 400 and response.status_code < 500:
            logger.warning(
                f"Error {response.status_code} encountered for IP: {client_ip}"
            )

        return response

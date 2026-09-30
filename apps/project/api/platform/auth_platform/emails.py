"""Verification emails for the public calculator."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.common.utils.mail import attach_inline_images

logger = logging.getLogger(__name__)


def send_lookup_code(email, code, *, request=None):
    """Send a code without exposing delivery failures to the public endpoint."""
    try:
        html = render_to_string(
            'auth_platform/email/lookup_code.html', {'code': code}, request=request,
        )
        message = EmailMultiAlternatives(
            subject='Tu código de verificación',
            body=strip_tags(html.replace('</p>', '</p>\n')),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        message.attach_alternative(html, 'text/html')
        message.mixed_subtype = 'related'
        attach_inline_images(message, {
            'membrete': 'assets/imgs/consultar_proceso/membrete-paz-y-salvo.jpg',
        })
        if not message.send(fail_silently=False):
            logger.error('No se pudo enviar el código de verificación de calculadora.')
    except Exception:
        logger.exception('Fallo al enviar el código de verificación de calculadora.')

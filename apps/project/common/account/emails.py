"""
El correo que lleva el codigo de acceso.

De quien viene y a quien se responde
------------------------------------
Sale del `DEFAULT_FROM_EMAIL` --el buzon que de verdad esta autorizado a
enviar por el dominio-- y contesta a la direccion de direccion. Es la misma
separacion que en los avisos del gestor de procesos: quien firma el envio no
tiene por que ser quien atiende la respuesta, y poner el buzon de direccion
en el `From` haria que los envios fallaran la autenticacion del dominio.

Por que sale con `fail_silently=False`
--------------------------------------
Si el correo no llega a salir, quien lo espera se quedaria mirando una
pantalla que promete un codigo que no va a llegar. Es mejor que la pantalla
lo diga, y para eso el fallo tiene que subir: lo recoge `otp_login.issue()`,
que ademas descarta el codigo emitido.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from apps.common.utils.mail import attach_inline_images

logger = logging.getLogger(__name__)

#: A donde contesta quien le da a «responder».
REPLY_TO = getattr(
    settings, 'ACCOUNT_REPLY_TO', 'info@propensionesabogados.com'
)

#: A quien avisar si a alguien le llega un codigo que no ha pedido, que es la
#: senal de que otro esta intentando entrar en su cuenta.
CONTACT_EMAIL = getattr(
    settings, 'OTP_CONTACT_EMAIL', 'info@propensionesabogados.com'
)

#: El membrete viaja dentro del mensaje. El porque, en `apps.common.utils.mail`.
INLINE_IMAGES = {
    'membrete': 'assets/imgs/consultar_proceso/membrete-paz-y-salvo.jpg',
}


def send_login_otp_email(*, user, code: str, minutes: int) -> None:
    """Manda el codigo de acceso a la direccion de la cuenta."""
    contexto = {
        'name': user.get_short_name() or user.get_username(),
        'code': code,
        'minutes': minutes,
        'contact_email': CONTACT_EMAIL,
        'year': timezone.localtime().year,
    }

    cuerpo_html = render_to_string('account/email/login_otp.html', contexto)

    mensaje = EmailMultiAlternatives(
        subject=_('Your access code for Propensiones® Abogados'),
        # La version en texto: se deriva del HTML en vez de mantener dos
        # plantillas, que es como acaban diciendo cosas distintas. El salto
        # tras cada parrafo evita que salga todo en un renglon con el codigo
        # pegado a la frase anterior.
        body=strip_tags(cuerpo_html.replace('</p>', '</p>\n')),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[REPLY_TO],
    )
    mensaje.attach_alternative(cuerpo_html, 'text/html')
    # `related` y no `mixed`: los adjuntos son partes del HTML, no ficheros
    # sueltos que el lector deba ofrecer.
    mensaje.mixed_subtype = 'related'
    attach_inline_images(mensaje, INLINE_IMAGES)

    mensaje.send(fail_silently=False)
    logger.info('Codigo de acceso enviado a la cuenta %s.', user.pk)

"""
Los correos de la cuenta: el codigo de acceso y el enlace para cambiar la clave.

De quien vienen y a quien se responde
-------------------------------------
Salen del `DEFAULT_FROM_EMAIL` --el buzon que de verdad esta autorizado a
enviar por el dominio-- y contestan a la direccion de direccion. Es la misma
separacion que en los avisos del gestor de procesos: quien firma el envio no
tiene por que ser quien atiende la respuesta, y poner el buzon de direccion
en el `From` haria que los envios fallaran la autenticacion del dominio.

Uno solo para el codigo
-----------------------
La maqueta, el membrete y el pie del correo del codigo viven en
`apps.common.utils.otp_email`, que es el mismo mensaje que mandaria cualquier
otra pantalla con un codigo. Aqui solo esta lo que distingue a este: el asunto
y la frase que dice para que sirve.

Por que salen con `fail_silently=False`
---------------------------------------
Si el correo del codigo no llega a salir, quien lo espera se quedaria mirando
una pantalla que promete un codigo que no va a llegar. Es mejor que la pantalla
lo diga, y para eso el fallo tiene que subir: lo recoge `otp_login.issue()`,
que ademas descarta el codigo emitido.

El de la recuperacion de clave es el caso contrario, y lo trata quien lo llama
(`views.ForgotPasswordFormView`): ahi un fallo de envio no puede distinguirse
desde fuera, o la pantalla diria quien tiene cuenta.
"""

import logging
from html import unescape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from apps.common.utils.mail import attach_inline_images
from apps.common.utils.otp_email import contact_email, send_otp_email

logger = logging.getLogger(__name__)

#: A donde contesta quien le da a «responder».
REPLY_TO = getattr(
    settings, 'ACCOUNT_REPLY_TO', 'info@propensionesabogados.com'
)

#: A quien avisar si a alguien le llega un codigo que no ha pedido, que es la
#: senal de que otro esta intentando entrar en su cuenta.
CONTACT_EMAIL = contact_email()

#: El membrete viaja dentro del mensaje. El porque, en `apps.common.utils.mail`.
INLINE_IMAGES = {
    'membrete': 'assets/imgs/consultar_proceso/membrete-paz-y-salvo.jpg',
}


def send_login_otp_email(*, user, code: str, minutes: int) -> None:
    """Manda el codigo de acceso a la direccion de la cuenta."""
    send_otp_email(
        to=user.email,
        subject=_('Your access code for Propensiones® Abogados'),
        instruction=_('Use the following code to sign in to your account.'),
        code=code,
        minutes=minutes,
        greeting_name=user.get_short_name() or user.get_username(),
        reply_to=REPLY_TO,
    )
    logger.info('Codigo de acceso enviado a la cuenta %s.', user.pk)


def send_password_reset_email(*, user, reset_url: str, minutes: int) -> None:
    """
    Manda el enlace para fijar una clave nueva.

    `reset_url` llega ya construido por la vista con `PUBLIC_BASE_URL`, nunca
    con la cabecera `Host` de la peticion: esa la pone el cliente, y un enlace
    de restablecimiento que apunte donde el atacante diga es justo lo que se
    evita.
    """
    contexto = {
        'name': user.get_short_name() or user.get_username(),
        'reset_url': reset_url,
        'minutes': minutes,
        'contact_email': CONTACT_EMAIL,
        'year': timezone.localtime().year,
    }

    cuerpo_html = render_to_string('account/email/password_reset.html', contexto)

    mensaje = EmailMultiAlternatives(
        subject=_('Reset your password for Propensiones® Abogados'),
        # La version en texto se deriva del HTML en vez de mantener dos
        # plantillas, que es como acaban diciendo cosas distintas. El enlace
        # va tambien escrito en un parrafo propio: `strip_tags` se lleva el
        # `href` y sin eso el texto plano no tendria por donde seguir. Y
        # `unescape` es imprescindible: la plantilla escribe `&` como `&amp;`
        # y, sin deshacerlo, el enlace del texto plano llegaria roto.
        body=unescape(strip_tags(cuerpo_html.replace('</p>', '</p>\n'))),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[REPLY_TO],
    )
    mensaje.attach_alternative(cuerpo_html, 'text/html')
    mensaje.mixed_subtype = 'related'
    attach_inline_images(mensaje, INLINE_IMAGES)

    mensaje.send(fail_silently=False)
    logger.info('Enlace de cambio de clave enviado a la cuenta %s.', user.pk)

"""
Los correos que el despacho le manda al cliente.

Que se manda
------------
Dos cosas, y las dos nacen de una nota del expediente (`CaseNoteModel`):

- una **novedad** que alguien del despacho escribe --que falta un documento,
  que el asunto esta en espera, lo que sea--, si marca la casilla de aviso;
- un **avance de etapa**, que lo escribe el sistema al guardar un asunto cuyo
  estado cambio, tambien solo si se marca la casilla.

De quien viene y a quien se responde
------------------------------------
Sale del `DEFAULT_FROM_EMAIL` configurado en Django --el buzon que de verdad
esta autorizado a enviar por el dominio-- y lleva `Reply-To` a la direccion
de direccion (`CASE_MANAGER_REPLY_TO`). Es la separacion de siempre: quien
firma el envio no tiene por que ser quien atiende la respuesta, y poner el
buzon de direccion en el `From` haria que los envios fallaran la
autenticacion del dominio.

Por que las imagenes van dentro y no enlazadas
----------------------------------------------
El membrete y la firma viajan **dentro del propio mensaje**, adjuntos y
referenciados con `cid:`, porque casi todos los clientes de correo bloquean
las imagenes remotas. El como esta en `apps.common.utils.mail`, que es el
mismo mecanismo que usa el correo del codigo de acceso; aqui solo queda que
imagenes lleva este correo.

Y siempre se manda tambien la version en texto plano. No es un adorno: un
correo solo-HTML puntua peor en los filtros de spam, y hay quien lee el
correo en texto.
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

#: A donde contesta el cliente cuando le da a «responder».
REPLY_TO = getattr(
    settings, 'CASE_MANAGER_REPLY_TO', 'director@propensionesabogados.com'
)

#: Las imagenes que van dentro del mensaje, con el `cid` por el que las
#: referencia la plantilla. La ruta es relativa a `STATICFILES_DIRS[0]`, y no
#: a `STATIC_ROOT`, para que funcione sin haber pasado `collectstatic`.
INLINE_IMAGES = {
    'membrete': 'assets/imgs/consultar_proceso/membrete-paz-y-salvo.jpg',
    'firma': 'assets/imgs/consultar_proceso/firma.png',
}


def send_case_note(note, *, request=None) -> bool:
    """
    Le manda al cliente el correo de una nota. Devuelve si salio.

    No se manda y devuelve `False` --sin reventar-- cuando el cliente no tiene
    correo o la nota no es para el. Las dos son situaciones normales, no
    errores: hay clientes de los que solo se tiene el telefono, y hay notas
    que son para el expediente.

    Marca `notified_at` **solo si el envio salio**. Si se marcara antes,
    un fallo del servidor de correo dejaria el expediente diciendo que se
    aviso a alguien a quien no se aviso, que es peor que no haber avisado.
    """
    cliente = note.case.client

    if not note.visible_to_client:
        return False

    if not cliente.email:
        logger.info(
            'El cliente %s no tiene correo; la nota «%s» no se envia.',
            cliente.identification, note.title,
        )
        return False

    asunto = _('%(kind)s — your case with Propensiones® Abogados') % {
        'kind': note.get_kind_display()
    }

    contexto = {
        'note': note,
        'case': note.case,
        'client': cliente,
        'reply_to': REPLY_TO,
        'year': timezone.localtime().year,
    }
    cuerpo_html = render_to_string(
        'case_manager/email/case_note.html', contexto, request=request
    )

    mensaje = EmailMultiAlternatives(
        subject=asunto,
        # La version en texto: se deriva del HTML en vez de mantener dos
        # plantillas, que es como acaban diciendo cosas distintas.
        body=strip_tags(cuerpo_html),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[cliente.email],
        reply_to=[REPLY_TO],
    )
    mensaje.attach_alternative(cuerpo_html, 'text/html')
    # `related` y no `mixed`: le dice al cliente de correo que los adjuntos
    # son partes del HTML, no ficheros sueltos que el lector deba ofrecer.
    mensaje.mixed_subtype = 'related'
    attach_inline_images(mensaje, INLINE_IMAGES)

    try:
        enviados = mensaje.send(fail_silently=False)
    except Exception:
        # Un fallo del servidor de correo no puede tumbar el guardado del
        # expediente: la nota ya esta escrita y eso es lo que no se puede
        # perder. Se registra y se sigue.
        logger.exception(
            'Fallo al enviar la nota «%s» a %s.', note.title, cliente.email
        )
        return False

    if not enviados:
        return False

    note.notified_at = timezone.now()
    note.save(update_fields=['notified_at', 'updated'])
    logger.info(
        'Nota «%s» enviada a %s.', note.title, cliente.email
    )
    return True

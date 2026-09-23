"""
Los correos que el despacho le manda al cliente.

Que se manda
------------
Tres cosas. Dos nacen de una nota del expediente (`CaseNoteModel`):

- una **novedad** que alguien del despacho escribe --que falta un documento,
  que el asunto esta en espera, lo que sea--, si marca la casilla de aviso;
- un **avance de etapa**, que lo escribe el sistema al guardar un asunto cuyo
  estado cambio, tambien solo si se marca la casilla.

Y la tercera es el **codigo de acceso al portal**, que no es un aviso sino la
puerta: quien lo recibe demuestra que controla el correo que consta en el
expediente. Por eso sale con `fail_silently=False` --si no llega a salir, la
pantalla tiene que decirlo en vez de prometer un codigo que no va a llegar--
mientras que los avisos se tragan el fallo y siguen.

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

#: El correo del codigo solo lleva el membrete.
#:
#: La firma escaneada del representante legal no pinta nada en un correo
#: automatico: no hay nada firmado que enviar, son unos 40 KB por mensaje, y
#: una firma que viaja en cada codigo de acceso es una firma que acaba
#: circulando. Los avisos del expediente si la llevan, porque alli el
#: despacho esta comunicando algo.
ACCESS_CODE_IMAGES = {
    'membrete': INLINE_IMAGES['membrete'],
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


def send_access_code(*, client, code: str, minutes: int) -> None:
    """
    Le manda al cliente el codigo con el que entra a ver su proceso.

    Sale con `fail_silently=False` al contrario que los avisos de arriba, y no
    es una incoherencia: un aviso que no sale deja una nota sin leer, y eso se
    arregla despues; un codigo que no sale deja a alguien mirando un campo
    vacio en una pantalla que le prometio un correo. El fallo lo recoge
    `portal_otp.issue()`, que entonces no anota nada y deja que la pantalla lo
    diga.
    """
    contexto = {
        'client': client,
        'code': code,
        'minutes': minutes,
        'reply_to': REPLY_TO,
        'year': timezone.localtime().year,
    }
    cuerpo_html = render_to_string(
        'case_manager/email/access_code.html', contexto
    )

    mensaje = EmailMultiAlternatives(
        subject=_('Your access code — Propensiones® Abogados'),
        # El salto tras cada parrafo evita que la version en texto salga en un
        # solo renglon con el codigo pegado a la frase anterior.
        body=strip_tags(cuerpo_html.replace('</p>', '</p>\n')),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[client.email],
        reply_to=[REPLY_TO],
    )
    mensaje.attach_alternative(cuerpo_html, 'text/html')
    mensaje.mixed_subtype = 'related'
    attach_inline_images(mensaje, ACCESS_CODE_IMAGES)

    mensaje.send(fail_silently=False)
    logger.info('Codigo de acceso al portal enviado al cliente %s.', client.pk)

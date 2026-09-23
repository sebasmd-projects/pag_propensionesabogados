"""
Lo comun a los correos que manda el sitio: que las imagenes se vean.

Casi todos los clientes de correo **bloquean las imagenes remotas** por
defecto: son el metodo clasico para saber si alguien abrio un mensaje. Un
membrete servido desde `propensionesabogados.com` sale como un cuadro roto
hasta que la persona pulsa «mostrar imagenes», y muchas no lo pulsan nunca.
En el correo que lleva un codigo de acceso eso es justo lo que no conviene:
el mensaje que hay que reconocer de un vistazo llega descuadrado.

La solucion es vieja y sigue siendo la unica que funciona en todas partes:
las imagenes viajan **dentro** del mensaje, adjuntas y referenciadas con
`cid:`. Se ven sin pedir permiso y no delatan la apertura.

Esto estaba escrito en `case_manager.emails` y ahora lo necesita tambien el
correo del codigo de acceso, asi que vive aqui y alli solo queda la lista de
imagenes de cada correo.
"""

import logging
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def static_source(relative: str) -> Path | None:
    """
    El fichero en disco de un estatico, mirando donde de verdad esta.

    Primero en `STATICFILES_DIRS` --el codigo fuente-- y despues en
    `STATIC_ROOT`: en desarrollo lo segundo puede no existir todavia, y en
    produccion lo primero existe igualmente.
    """
    candidatos = [
        Path(d) / relative for d in getattr(settings, 'STATICFILES_DIRS', [])
    ]

    raiz = getattr(settings, 'STATIC_ROOT', None)

    if raiz and raiz != 'None':
        candidatos.append(Path(raiz) / relative)

    return next((ruta for ruta in candidatos if ruta.is_file()), None)


def attach_inline_images(
    message: EmailMultiAlternatives, images: dict
) -> None:
    """
    Mete las imagenes en el mensaje y las marca como `inline`.

    `Content-ID` es lo que enlaza `<img src="cid:membrete">` con el adjunto.
    Va entre `<>` porque asi lo pide el RFC 2392, y sin los angulos hay
    clientes que no lo resuelven y ensenan el cuadro roto igual.

    `Content-Disposition: inline` evita lo otro: que el cliente ensene las
    imagenes como ficheros adjuntos al final del mensaje, que es lo que hace
    si no se le dice.

    Una imagen que falte no tumba el envio: el correo sale sin ella, con su
    `alt`, y queda el aviso en el registro. El mensaje importa mas que el
    membrete.

    Args:
        message: el mensaje, que debe llevar ya `mixed_subtype = 'related'`.
        images: `{cid: ruta relativa al estatico}`.
    """
    for cid, relative in images.items():
        ruta = static_source(relative)

        if ruta is None:
            logger.warning(
                'No se encontro la imagen %s para incrustar en el correo; '
                'el mensaje sale sin ella.',
                relative,
            )
            continue

        imagen = MIMEImage(ruta.read_bytes())
        imagen.add_header('Content-ID', f'<{cid}>')
        imagen.add_header('Content-Disposition', 'inline', filename=ruta.name)
        message.attach(imagen)

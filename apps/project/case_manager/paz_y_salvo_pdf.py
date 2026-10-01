"""
El PDF original del paz y salvo, sin codigos.

Reproduce `templates/case_manager/paz_y_salvo.html` (hoja A4, membrete, logo,
textos y firma) con reportlab, porque quien certifica es gea y gea recibe un
PDF. Ese PDF sale **sin QR ni codigo de barras**: gea los estampa en las
posiciones de `placement()`, asi que aqui solo se deja el hueco.

Dos huecos, en puntos PDF con origen abajo a la izquierda (lo que pide gea):

* QR: a la derecha del logo, centrado verticalmente con el.
* Codigo de barras: donde el diseno anterior ponia el NIT del despacho, entre
  el nombre de la sociedad y la descripcion de la entidad.

`placement()` es una funcion pura de constantes: reintentar una certificacion
no obliga a regenerar el PDF para saber donde estan los huecos.
"""

from io import BytesIO

from django.contrib.staticfiles import finders
from django.utils import timezone
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from xml.sax.saxutils import escape

from .templatetags.case_manager_extras import client_number

PAGE_W, PAGE_H = 210 * mm, 297 * mm
MARGIN_X = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

LOGO = 'assets/imgs/consultar_proceso/membrete-paz-y-salvo.jpg'
FIRMA = 'assets/imgs/consultar_proceso/firma.png'

LOGO_W = 34 * mm
LOGO_TOP = 9 * mm            # margen superior de la hoja
QR_SIZE = 28 * mm

#: Code128 de gea (876 x 241 px con sus opciones por defecto): relacion 3.63.
BARCODE_W = 204.0
BARCODE_H = 56.0

INK = (0.071, 0.149, 0.227)          # #12263a
MUTED = (0.294, 0.357, 0.42)         # #4b5b6b
RULE = (0.749, 0.784, 0.824)         # #bfc8d2

MESES = (
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
    'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
)


def _static(path: str) -> str:
    found = finders.find(path)
    if not found:
        raise FileNotFoundError(path)
    return found


def _image_height(path: str, width: float) -> float:
    from PIL import Image
    with Image.open(path) as image:
        return width * image.height / image.width


def _logo_box():
    """`(x, y, w, h)` del logo en puntos, origen abajo a la izquierda."""
    height = _image_height(_static(LOGO), LOGO_W)
    return (PAGE_W - LOGO_W) / 2, PAGE_H - LOGO_TOP - height, LOGO_W, height


def qr_box() -> dict:
    """El QR, a la derecha del logo y a su altura (centro con centro)."""
    _, logo_y, _, logo_h = _logo_box()
    size = QR_SIZE
    return {
        'page': 1,
        'x': round(PAGE_W - MARGIN_X - size, 2),
        'y': round(logo_y + logo_h / 2 - size / 2, 2),
        'size': round(size, 2),
    }


# Cursor vertical fijo del membrete: se calcula igual al dibujar y al
# colocar el codigo de barras, para que el hueco y el texto no se pisen.
_LOGO_MARGIN_BOTTOM = 7 * mm
_DIR_SIZE, _EMPRESA_SIZE = 15, 19


def _header_cursor() -> dict:
    """Ordenadas (desde abajo) de cada bloque del membrete."""
    _, logo_y, _, _ = _logo_box()
    y = logo_y - _LOGO_MARGIN_BOTTOM
    dir_base = y - _DIR_SIZE                      # linea base "La Direccion"
    y = dir_base - _DIR_SIZE * 0.25 - 1.5 * mm
    empresa_base = y - _EMPRESA_SIZE
    y = empresa_base - _EMPRESA_SIZE * 0.25 - 1 * mm
    bar_top = y
    bar_bottom = bar_top - BARCODE_H
    return {
        'dir_base': dir_base,
        'empresa_base': empresa_base,
        'bar_top': bar_top,
        'bar_bottom': bar_bottom,
        'after_bar': bar_bottom - 3 * mm,
    }


def barcode_box() -> dict:
    """El Code128, donde antes iba el NIT del despacho."""
    cursor = _header_cursor()
    return {
        'page': 1,
        'x': round((PAGE_W - BARCODE_W) / 2, 2),
        'y': round(cursor['bar_bottom'], 2),
        'width': BARCODE_W,
        'height': BARCODE_H,
    }


def placement() -> dict:
    """El `placement` que espera gea, en puntos PDF."""
    return {'qr': qr_box(), 'barcode': barcode_box()}


def _style(name, font, size, leading=None, align=0, color=INK, **extra):
    return ParagraphStyle(
        name, fontName=font, fontSize=size,
        leading=leading or size * 1.2, alignment=align,
        textColor=color, **extra,
    )


def _para(canv, text, style, x, top, width):
    """Dibuja un parrafo con su borde superior en `top`; devuelve su base."""
    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, PAGE_H)
    paragraph.drawOn(canv, x, top - height)
    return top - height


def _fecha(dt):
    return dt.day, MESES[dt.month - 1], dt.year


def build_pdf(*, case, authorized_at, reference: str) -> bytes:
    """
    El paz y salvo de `case`, con la fecha en que se autorizo.

    `authorized_at` es la fecha congelada del documento: nunca la de hoy.
    """
    issued = timezone.localtime(authorized_at)
    day, month, year = _fecha(issued)
    client = case.client
    short_id = str(case.pk)[:8]

    buffer = BytesIO()
    canv = canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    canv.setTitle('Paz y salvo')
    canv.setAuthor('Propensiones S.A.S.')
    canv.setSubject(f'Caso {short_id}')

    # --- Membrete ---------------------------------------------------------
    lx, ly, lw, lh = _logo_box()
    canv.drawImage(_static(LOGO), lx, ly, lw, lh, mask='auto')
    cursor = _header_cursor()

    canv.setFillColorRGB(*INK)
    canv.setFont('Times-Bold', _DIR_SIZE)
    canv.drawCentredString(PAGE_W / 2, cursor['dir_base'],
                           'La Dirección General')
    canv.setFont('Times-Bold', _EMPRESA_SIZE)
    canv.drawCentredString(PAGE_W / 2, cursor['empresa_base'],
                           'PROPENSIONES S.A.S.')

    # (Aqui va el Code128 que estampa gea, en `barcode_box()`.)
    entidad = _style('entidad', 'Times-Roman', 12.5, 12.5 * 1.18,
                     align=TA_CENTER)
    y = _para(
        canv,
        'Entidad Privada en Asesorías y Trámites Legales a Nivel Nacional '
        'e Internacional',
        entidad, (PAGE_W - 160 * mm) / 2, cursor['after_bar'] - 3 * mm,
        160 * mm,
    )

    # --- Titulo -----------------------------------------------------------
    titulo = _style('titulo', 'Times-Bold', 15, 15 * 1.15, align=TA_CENTER)
    y = _para(
        canv, 'PAZ Y SALVO POR CONCEPTO DE MANDATO PROFESIONAL', titulo,
        MARGIN_X, y - 7 * mm, CONTENT_W,
    )

    ref = _style('ref', 'Helvetica', 9.5, 12, align=TA_CENTER, color=MUTED)
    y = _para(
        canv,
        f'Caso <b>{escape(short_id)}</b> &nbsp;|&nbsp; Referencia: '
        f'<b>{escape(reference)}</b>',
        ref, MARGIN_X, y - 3 * mm, CONTENT_W,
    )

    # --- Cuerpo -----------------------------------------------------------
    texto = _style('texto', 'Helvetica', 11, 11 * 1.35, align=TA_JUSTIFY)
    if client.is_nit:
        quien = 'la sociedad o persona jurídica'
        tipo = 'NIT'
    else:
        quien = 'el(la) señor(a)'
        tipo = str(client.get_identification_type_display()).lower()

    y = _para(
        canv,
        f'Por medio del presente documento se deja constancia de que {quien} '
        f'<b>{escape(client.full_name)}</b>, identificado(a) con '
        f'{escape(tipo)} No. <b>{escape(client_number(client))}</b>, se '
        'encuentra <b>A PAZ Y SALVO</b> por concepto de honorarios '
        'profesionales derivados del acompañamiento, asesoría y gestión '
        'jurídica prestada dentro del trámite '
        f'<b>{escape(str(case.paz_y_salvo_subject))}</b>.',
        texto, MARGIN_X, y - 6 * mm, CONTENT_W,
    )
    y = _para(
        canv,
        'La presente <b>PAZ Y SALVO</b> comprende los honorarios pactados '
        'por el acompañamiento jurídico realizado en la etapa surtida, '
        'conforme a la información registrada en el sistema de seguimiento '
        'de <b>Propensiones® Abogados Internacional</b>.',
        texto, MARGIN_X, y - 5 * mm, CONTENT_W,
    )
    fecha = _style('fecha', 'Helvetica', 11, 11 * 1.35)
    y = _para(
        canv,
        f'Se expide en Armenia, Quindío, a los {day} días del mes de '
        f'{month} de {year}, para los fines pertinentes.',
        fecha, MARGIN_X, y - 5 * mm, CONTENT_W,
    )

    # --- Firma ------------------------------------------------------------
    cordial = _style('cordial', 'Helvetica-Oblique', 11, 13)
    y = _para(canv, 'Cordialmente,', cordial, MARGIN_X, y - 5 * mm, CONTENT_W)

    firma_w = 58 * mm
    firma_h = _image_height(_static(FIRMA), firma_w)
    firma_top = y - 3 * mm
    canv.drawImage(_static(FIRMA), MARGIN_X - 2 * mm, firma_top - firma_h,
                   firma_w, firma_h, mask='auto')
    y = firma_top - firma_h + 4 * mm

    nombre = _style('nombre', 'Helvetica-Bold', 10.8, 12.4)
    y = _para(canv, 'Jorge Uriel Vega Londoño', nombre, MARGIN_X, y,
              CONTENT_W)
    chico = _style('chico', 'Helvetica', 10.5, 12.6)
    for line in ('Representante legal',
                 'Correo Firma PP: notificaciones@propensionesabogados.com',
                 'Celular: +57 301 228 3818'):
        y = _para(canv, line, chico, MARGIN_X, y, CONTENT_W)

    # --- Constancia -------------------------------------------------------
    y -= 4 * mm
    canv.setStrokeColorRGB(*RULE)
    canv.setLineWidth(0.75)
    canv.line(MARGIN_X, y, PAGE_W - MARGIN_X, y)
    constancia = _style('constancia', 'Helvetica', 8.7, 8.7 * 1.28,
                        color=MUTED)
    _para(
        canv,
        '<b>Constancia electrónica de generación.</b><br/>'
        'Documento generado electrónicamente por el sistema de '
        'Propensiones® Abogados Internacional.<br/>'
        f'<b>Fecha de generación:</b> {issued:%d/%m/%Y}. &nbsp; '
        f'<b>Hora de generación:</b> {issued:%H:%M}.<br/>'
        '<b>Firmado por:</b> Jorge Uriel Vega Londoño – Representante legal.',
        constancia, MARGIN_X, y - 2.5 * mm, CONTENT_W,
    )

    canv.showPage()
    canv.save()
    return buffer.getvalue()


def source_filename(case) -> str:
    return f'paz-y-salvo-{str(case.pk)[:8]}.pdf'

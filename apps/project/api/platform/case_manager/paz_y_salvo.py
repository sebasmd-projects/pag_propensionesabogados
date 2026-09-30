"""
El ciclo de vida del paz y salvo certificado.

    autorizar -> documento PENDING -> (hilo) PDF -> gea -> copia -> CERTIFIED
    retirar   -> documento REVOKED -> (hilo) revocar en gea

Nada de esto rompe la autorizacion: si gea esta caido o sin configurar, el
documento queda PENDING o FAILED con su `last_error`, la autorizacion sigue en
pie y `certify_pending_paz_y_salvo` lo reintenta con la misma
`idempotency_key`, de modo que reintentar no duplica el certificado.

Los hilos son daemon y no reciben el request: ni el usuario, ni la sesion, ni
la conexion de BD del request. Cada uno abre y cierra la suya, como el correo
de codigos de `auth_platform`.
"""

import logging
import re
import threading

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import close_old_connections, transaction
from django.utils import timezone
from django.utils.translation import gettext as _, override

from . import gea_client, paz_y_salvo_pdf
from .models import CaseModel, PazYSalvoDocumentModel

logger = logging.getLogger(__name__)

Status = PazYSalvoDocumentModel.Status

#: NIT del despacho tal como va en el codigo de barras: sin puntos.
DESPACHO_NIT = '901409813-7'


# ---------------------------------------------------------------------------
# Lo que lleva el documento
# ---------------------------------------------------------------------------

def qr_url(case_id) -> str:
    """La URL publica que codifica el QR."""
    return (f'{settings.PAZ_Y_SALVO_PUBLIC_BASE}/consultar/proceso/'
            f'{case_id}/paz-y-salvo/')


def barcode_text(case_id, authorized_at) -> str:
    """
    `264e7535 20260930 901409813-7`: caso, fecha de autorizacion (AAAAMMDD,
    hora de Bogota) y NIT del despacho, separados por un espacio.

    Todo cabe en lo que acepta el validador de gea (letras, digitos, espacio,
    `.`, `_` y `-`; sin `//`, `:`, etc.) y mide 29 caracteres, por debajo de
    los 48 que gea recomienda para que el simbolo no salga demasiado ancho.
    """
    day = timezone.localtime(authorized_at).strftime('%Y%m%d')
    return f'{str(case_id)[:8]} {day} {DESPACHO_NIT}'


def _clean(text: str, maxlen: int = 200) -> str:
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', text or '').strip()[:maxlen]


def _short_error(error) -> str:
    return _clean(str(error) or type(error).__name__, 500)


# ---------------------------------------------------------------------------
# Hilos
# ---------------------------------------------------------------------------

def _run(target, *args, **kwargs):
    try:
        target(*args, **kwargs)
    except Exception:
        logger.exception('Paz y salvo: fallo inesperado en el hilo.')
    finally:
        close_old_connections()


def _spawn(target, *args, **kwargs):
    try:
        threading.Thread(
            target=_run, args=(target, *args), kwargs=kwargs,
            daemon=True).start()
    except Exception:
        logger.exception('Paz y salvo: no se pudo iniciar el hilo.')


def start_certification(document_id, *, force=False):
    _spawn(certify, document_id, force=force)


def start_revocation(document_id):
    _spawn(revoke_in_gea, document_id)


# ---------------------------------------------------------------------------
# Autorizar y retirar (dentro de una transaccion del llamador)
# ---------------------------------------------------------------------------

def authorize(case: CaseModel) -> PazYSalvoDocumentModel:
    """Autoriza el paz y salvo y encola su certificacion."""
    now = timezone.now()

    # Un solo documento vigente por asunto: si quedara alguno, se retira.
    for stale in PazYSalvoDocumentModel.objects.select_for_update().filter(
            case=case).exclude(status=Status.REVOKED):
        _mark_revoked(stale, now)

    case.paz_y_salvo_authorized = True
    case.paz_y_salvo_authorized_at = now
    case.save(update_fields=[
        'paz_y_salvo_authorized', 'paz_y_salvo_authorized_at', 'updated'])

    document = PazYSalvoDocumentModel(
        case=case,
        authorized_at=now,
        reference_snapshot=_clean(case.public_reference, 255),
    )
    document.idempotency_key = f'paz-y-salvo-{document.pk}'
    document.save()

    transaction.on_commit(lambda: start_certification(document.pk))
    return document


def revoke(case: CaseModel):
    """Retira el paz y salvo y pide la revocacion en gea."""
    now = timezone.now()
    case.paz_y_salvo_authorized = False
    case.paz_y_salvo_authorized_at = None
    case.save(update_fields=[
        'paz_y_salvo_authorized', 'paz_y_salvo_authorized_at', 'updated'])

    for document in PazYSalvoDocumentModel.objects.select_for_update().filter(
            case=case).exclude(status=Status.REVOKED):
        _mark_revoked(document, now)


def sync_authorization(case: CaseModel, was_authorized: bool):
    """
    Para quien guardo `paz_y_salvo_authorized` por otra via (formulario del
    asunto, admin): si la casilla cambio, hace lo mismo que el boton del
    listado. Dentro de una transaccion.
    """
    if case.paz_y_salvo_authorized == was_authorized:
        return
    if case.paz_y_salvo_authorized:
        authorize(case)
    else:
        revoke(case)


def _mark_revoked(document, now):
    document.status = Status.REVOKED
    document.revoked_at = now
    document.save(update_fields=['status', 'revoked_at', 'updated'])
    # Sin id de gea todavia no hay nada que revocar alli: si una
    # certificacion estaba en vuelo, se revoca sola al terminar.
    if document.gea_document_id:
        transaction.on_commit(lambda: start_revocation(document.pk))


# ---------------------------------------------------------------------------
# Certificar
# ---------------------------------------------------------------------------

def _fail(document, message, *, status=Status.FAILED):
    """Deja constancia del error sin pisar un REVOKED que llegara en medio."""
    PazYSalvoDocumentModel.objects.filter(pk=document.pk).exclude(
        status__in=(Status.REVOKED, Status.CERTIFIED),
    ).update(status=status, last_error=_short_error(message),
             updated=timezone.now())


@override('es')
def certify(document_id, *, force=False):
    """
    Genera el PDF, lo manda a gea y guarda la copia distribuible.

    Idempotente y reintentable: a un documento CERTIFIED o REVOKED no lo toca;
    uno PENDING/FAILED se rehace desde donde quedo. `force` ignora el tope de
    intentos (para el reintento manual del gestor).
    """
    document = (PazYSalvoDocumentModel.objects
                .select_related('case__client').get(pk=document_id))

    if document.status in (Status.CERTIFIED, Status.REVOKED):
        return document

    if not gea_client.is_configured():
        _fail(document, _('gea is not configured (GEA_CERT_API_BASE / SERVER_KEY).'),
              status=document.status)
        return _reload(document)

    if not force and document.attempts >= settings.PAZ_Y_SALVO_MAX_ATTEMPTS:
        return document

    PazYSalvoDocumentModel.objects.filter(pk=document.pk).update(
        attempts=document.attempts + 1)

    try:
        pdf = _source_pdf(document)
        result = gea_client.issue(
            pdf=pdf,
            filename=paz_y_salvo_pdf.source_filename(document.case),
            reference=_clean(
                f'{document.short_case_id} {document.reference_snapshot}'),
            title=f'Paz y salvo {document.short_case_id}',
            qr_payload=qr_url(document.case_id),
            barcode_text=barcode_text(document.case_id, document.authorized_at),
            idempotency_key=document.idempotency_key,
            placement=paz_y_salvo_pdf.placement(),
        )
        # Desde aqui gea ya tiene el documento: se guarda el id para poder
        # revocarlo aunque la descarga falle.
        PazYSalvoDocumentModel.objects.filter(pk=document.pk).update(
            gea_document_id=result['document_id'],
            gea_code=result['code'],
            verification_url=result['verification_url'],
            source_hash=result['source_hash'],
            public_copy_hash=result['public_copy_hash'],
        )
        copy = gea_client.download_public_copy(
            result['document_id'], result['public_copy_hash'])
    except gea_client.GeaError as error:
        logger.warning('Paz y salvo %s: %s', document.pk, error)
        _fail(document, error)
        return _reload(document)
    except Exception as error:
        logger.exception('Paz y salvo %s: fallo inesperado.', document.pk)
        _fail(document, _('Unexpected error (%(error)s).') % {'error': type(error).__name__})
        return _reload(document)

    with transaction.atomic():
        fresh = (PazYSalvoDocumentModel.objects.select_for_update()
                 .get(pk=document.pk))
        was_revoked = fresh.status == Status.REVOKED
        if not was_revoked:
            fresh.public_copy_file.save(
                'public.pdf', ContentFile(copy), save=False)
            fresh.status = Status.CERTIFIED
            fresh.certified_at = timezone.now()
            fresh.last_error = ''
            fresh.save()

    if was_revoked:
        # Se retiro mientras se certificaba: la certificacion recien hecha no
        # puede quedar vigente en gea.
        revoke_in_gea(fresh.pk)

    return _reload(document)


def _source_pdf(document) -> bytes:
    """El PDF original: el guardado, o uno nuevo con la fecha congelada."""
    if document.source_file:
        try:
            with document.source_file.open('rb') as handle:
                return handle.read()
        except (FileNotFoundError, OSError):
            pass

    pdf = paz_y_salvo_pdf.build_pdf(
        case=document.case,
        authorized_at=document.authorized_at,
        reference=document.reference_snapshot or '—',
    )
    document.source_file.save('source.pdf', ContentFile(pdf), save=False)
    PazYSalvoDocumentModel.objects.filter(pk=document.pk).update(
        source_file=document.source_file.name)
    return pdf


def _reload(document):
    return PazYSalvoDocumentModel.objects.get(pk=document.pk)


@override('es')
def revoke_in_gea(document_id):
    """Pide a gea revocar un documento retirado. Tolera fallos."""
    document = PazYSalvoDocumentModel.objects.get(pk=document_id)
    if (document.status != Status.REVOKED or not document.gea_document_id
            or document.gea_revoked):
        return document

    try:
        gea_client.revoke(document.gea_document_id, _('Withdrawn by the firm.'))
    except gea_client.GeaError as error:
        logger.warning('Paz y salvo %s: revocar en gea fallo: %s',
                       document.pk, error)
        PazYSalvoDocumentModel.objects.filter(pk=document.pk).update(
            last_error=_short_error(_('Revocation pending: %(error)s') % {'error': error}))
        return _reload(document)

    PazYSalvoDocumentModel.objects.filter(pk=document.pk).update(
        gea_revoked=True, last_error='')
    return _reload(document)

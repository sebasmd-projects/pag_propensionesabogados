"""
Cliente de la API de emisores externos de gea.

Tres llamadas (ver `gea_module_0/.../certificates/external.py`):

* `issue()`     POST /api/certificates/external/
* `download_public_copy()`  GET  /api/certificates/external/<id>/public-copy/
* `revoke()`    POST /api/certificates/external/<id>/revoke/

Reglas que se cumplen aqui y no en quien llama:

* TLS verificado (`verify=True`), timeouts siempre, **sin reintentos**: reintentar
  es cosa de `certify_pending_paz_y_salvo`, acotado por intentos, y no duplica
  porque `idempotency_key` es la del documento.
* La clave (`SERVER_KEY`) solo viaja en la cabecera `X-Issuer-Key`. Nunca
  se registra, ni se incluye en un mensaje de error.
* Sin redirecciones: una redireccion mandaria la clave a otro sitio.
* La respuesta se valida; no se confia en la URL de descarga que devuelve gea,
  se construye desde la base configurada.
"""

import hashlib
import json
import logging
import re
import uuid
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils.translation import gettext as _, override

logger = logging.getLogger(__name__)

API_PATH = '/api/certificates/external/'
MAX_COPY_BYTES = 60 * 1024 * 1024
ERROR_DETAIL_MAX = 300


class GeaError(Exception):
    """Fallo hablando con gea. `str()` es seguro para guardar y mostrar."""


class GeaNotConfigured(GeaError):
    """Falta la base o la clave: no se intenta nada."""


def _key() -> str:
    """`SERVER_KEY`; en la transicion, la variable vieja de gea si aun manda."""
    return getattr(settings, 'SERVER_KEY_LEGACY_GEA', '') or settings.SERVER_KEY


def is_configured() -> bool:
    return bool(settings.GEA_CERT_API_BASE and _key())


@override('es')
def _require_config():
    if not is_configured():
        raise GeaNotConfigured(
            _('gea is not configured (GEA_CERT_API_BASE / SERVER_KEY).')
        )


def _headers() -> dict:
    return {
        'X-Issuer': settings.GEA_ISSUER_SLUG,
        'X-Issuer-Key': _key(),
    }


def _url(suffix: str = '') -> str:
    return f'{settings.GEA_CERT_API_BASE}{API_PATH}{suffix}'


def _safe(text) -> str:
    """Recorta un texto ajeno y le quita la clave, por si la devolvieran."""
    text = str(text)[:ERROR_DETAIL_MAX]
    key = _key()
    return text.replace(key, '***') if key else text


@override('es')
def _request(method, url, **kwargs):
    try:
        return requests.request(
            method, url,
            headers=_headers(),
            timeout=settings.GEA_CERT_TIMEOUT,
            verify=True,
            allow_redirects=False,
            **kwargs,
        )
    except requests.RequestException as error:
        # No se incluye `error`: su texto puede llevar la URL completa.
        logger.warning('gea request failed: %s', type(error).__name__)
        raise GeaError(_('gea unreachable (%(error)s).') % {'error': type(error).__name__}) from None


@override('es')
def _error_from(response) -> GeaError:
    """Traduce una respuesta de error de gea a un mensaje corto."""
    status = response.status_code
    if 300 <= status < 400:
        location = response.headers.get('Location')
        if location:
            return GeaError(
                _('gea redirects to %(location)s: check GEA_CERT_API_BASE')
                % {'location': _safe(location)})
        return GeaError(
            _('gea returned a redirect without Location (HTTP %(status)s): '
              'check GEA_CERT_API_BASE') % {'status': status})
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}

    if status == 400 and body.get('error') == 'invalid_request':
        return GeaError(
            _('gea rejected the request (400, field %(field)s).')
            % {'field': _safe(body.get('field', ''))})
    if status == 403:
        return GeaError(_('gea refused the issuer key (403).'))
    if status == 422:
        return GeaError(_('gea could not certify the document (422).'))
    if status == 429:
        return GeaError(_('gea rate limit reached (429).'))
    return GeaError(_('gea answered HTTP %(status)s.') % {'status': status})


@override('es')
def _json_ok(response, allowed=(200, 201)) -> dict:
    if response.status_code not in allowed:
        raise _error_from(response)
    try:
        body = response.json()
    except ValueError:
        raise GeaError(_('gea answered with invalid JSON.')) from None
    if not isinstance(body, dict):
        raise GeaError(_('gea answered with an unexpected body.'))
    return body


@override('es')
def _text(body, name, *, required=True, maxlen=500) -> str:
    value = body.get(name)
    if value is None or value == '':
        if required:
            raise GeaError(_('gea response is missing "%(name)s".') % {'name': name})
        return ''
    if not isinstance(value, str) or len(value) > maxlen:
        raise GeaError(_('gea response has an invalid "%(name)s".') % {'name': name})
    return value


@override('es')
def issue(*, pdf: bytes, filename: str, reference: str, title: str,
          qr_payload: str, barcode_text: str, idempotency_key: str,
          placement: dict) -> dict:
    """
    Pide la certificacion. Devuelve los datos validados de la respuesta:
    `document_id, code, verification_url, source_hash, public_copy_hash,
    issued_at`.
    """
    _require_config()

    response = _request(
        'POST', _url(),
        data={
            'issuer': settings.GEA_ISSUER_SLUG,
            'reference': reference,
            'title': title,
            'qr_payload': qr_payload,
            'barcode_text': barcode_text,
            'idempotency_key': idempotency_key,
            'placement': json.dumps(placement),
        },
        files={'source': (filename, pdf, 'application/pdf')},
    )
    body = _json_ok(response)

    document_id = _text(body, 'document_id', maxlen=64)
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise GeaError(_('gea response has an invalid "document_id".')) from None

    verification_url = _text(body, 'verification_url', required=False)
    if verification_url and urlparse(verification_url).scheme not in (
            'http', 'https'):
        raise GeaError(_('gea response has an invalid "verification_url".'))

    source_hash = _text(body, 'source_hash', maxlen=128)
    public_copy_hash = _text(body, 'public_copy_hash', maxlen=128)
    for name, value in (('source_hash', source_hash),
                        ('public_copy_hash', public_copy_hash)):
        if not re.fullmatch(r'[0-9a-fA-F]{64}', value):
            raise GeaError(_('gea response has an invalid "%(name)s".') % {'name': name})

    return {
        'document_id': document_id,
        'code': _text(body, 'code', required=False, maxlen=64),
        'verification_url': verification_url,
        'source_hash': source_hash,
        'public_copy_hash': public_copy_hash,
        'issued_at': _text(body, 'issued_at', required=False, maxlen=64),
    }


@override('es')
def download_public_copy(document_id: str, expected_hash: str = '') -> bytes:
    """
    Baja la copia distribuible. Comprueba que es un PDF, que no es enorme y,
    si gea dio su hash, que coincide (sha256).
    """
    _require_config()
    try:
        uuid.UUID(str(document_id))
    except ValueError:
        raise GeaError(_('Invalid gea document id.')) from None

    response = _request(
        'GET', _url(f'{document_id}/public-copy/'), stream=True)
    try:
        if response.status_code != 200:
            raise _error_from(response)

        chunks, size = [], 0
        for chunk in response.iter_content(64 * 1024):
            size += len(chunk)
            if size > MAX_COPY_BYTES:
                raise GeaError(_('gea public copy is too large.'))
            chunks.append(chunk)
    except requests.RequestException as error:
        raise GeaError(
            _('gea download failed (%(error)s).') % {'error': type(error).__name__}) from None
    finally:
        response.close()

    data = b''.join(chunks)
    if not data.startswith(b'%PDF'):
        raise GeaError(_('gea public copy is not a PDF.'))
    if expected_hash and (
            hashlib.sha256(data).hexdigest() != expected_hash.lower()):
        raise GeaError(_('gea public copy does not match its hash.'))
    return data


@override('es')
def revoke(document_id: str, reason: str = '') -> dict:
    """Pide la revocacion (idempotente en gea)."""
    _require_config()
    try:
        uuid.UUID(str(document_id))
    except ValueError:
        raise GeaError(_('Invalid gea document id.')) from None

    response = _request(
        'POST', _url(f'{document_id}/revoke/'), data={'reason': reason[:1000]})
    return _json_ok(response, allowed=(200,))

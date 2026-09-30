"""
Receptor de informes de la politica de seguridad de contenido (CSP).

La politica va en modo `Content-Security-Policy-Report-Only` (ver
`CONTENT_SECURITY_POLICY_REPORT_ONLY` en `settings.py`): el navegador no
bloquea nada y manda a `report-uri` un JSON por cada cosa que bloquearia. Este
es ese destino. Ni `django-csp` ni gea traen uno, asi que es lo minimo:

* **No guarda nada en base de datos.** Cada informe es una linea de log, en el
  mismo `stderr.log` que rota `logs.py`.
* **Tiene cupo.** Cualquiera puede postear aqui, y una sola pagina con veinte
  scripts en linea manda veinte informes: 60 por minuto y por IP, y un cuerpo
  de 8 KiB como maximo. Pasado el cupo se descarta en silencio. Si la cache no
  responde tambien se descarta (fallo cerrado): perder informes es barato,
  llenar el log no.
* **Contesta siempre 204** a un POST, valga o no el informe: no hay nada que
  el navegador deba reintentar y a quien sondea no se le dice por que.
* **No apunta lo que puede ser un secreto.** `document-uri` de un enlace de
  cambio de clave lleva el token en la ruta, y `blocked-uri` de un `data:` es
  el propio contenido. De cada URI solo queda el origen mas los segmentos de
  ruta que son palabras cortas; el resto pasa a `*`. Sin query ni fragmento.
"""

import json
import logging
import re
from urllib.parse import urlsplit

from django.http import HttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt

from .throttling import RateLimit

logger = logging.getLogger('csp_report')

#: Cuerpo maximo que se lee. Un informe de verdad pesa menos de 1 KiB.
MAX_BODY_BYTES = 8 * 1024

#: Informes por IP y por minuto.
csp_report_ip = RateLimit('csp_report_ip', limit=60, window=60)

#: Campos que se apuntan, y su longitud maxima.
FIELDS = (
    'effective-directive', 'violated-directive', 'disposition',
    'line-number', 'column-number', 'status-code',
)
URI_FIELDS = ('document-uri', 'blocked-uri', 'source-file')

_WORD = re.compile(r'^[A-Za-z_-]{1,30}$')
_SAFE_VALUE = re.compile(r'[^A-Za-z0-9 _:.\'-]')


def scrub_uri(value) -> str:
    """El origen y las palabras de la ruta; sin query, fragmento ni tokens."""
    value = str(value or '')[:500]

    if not value:
        return ''

    parts = urlsplit(value)

    if not parts.scheme or not parts.netloc:
        # `inline`, `eval`, `data`, `blob`, `self`...: una palabra clave del
        # navegador o un esquema. Nunca el contenido de un `data:`.
        return _SAFE_VALUE.sub('', value.split(':', 1)[0])[:30]

    path = '/'.join(
        seg if (not seg or _WORD.match(seg)) else '*'
        for seg in parts.path.split('/')[:6]
    )

    host = _SAFE_VALUE.sub('', parts.hostname or '')[:100]

    return f'{parts.scheme}://{host}{path}'


def _clean(value) -> str:
    return _SAFE_VALUE.sub('', str(value))[:60]


def _reports(payload) -> list:
    """Los informes de un cuerpo, sea el formato antiguo o `application/reports+json`."""
    if isinstance(payload, dict):
        body = payload.get('csp-report')
        return [body] if isinstance(body, dict) else []

    if isinstance(payload, list):
        return [
            item.get('body')
            for item in payload[:10]
            if isinstance(item, dict)
            and item.get('type') == 'csp-violation'
            and isinstance(item.get('body'), dict)
        ]

    return []


def summarize(report: dict) -> dict:
    """Lo que se apunta de un informe, ya limpio."""
    line = {name: _clean(report[name]) for name in FIELDS if name in report}

    for name in URI_FIELDS:
        if name in report:
            line[name] = scrub_uri(report[name])

    # Las claves del formato nuevo van en camelCase.
    for camel, kebab in (
        ('effectiveDirective', 'effective-directive'),
        ('documentURL', 'document-uri'),
        ('blockedURL', 'blocked-uri'),
        ('sourceFile', 'source-file'),
    ):
        if camel in report and kebab not in line:
            line[kebab] = (
                scrub_uri(report[camel]) if kebab.endswith(('uri', 'file'))
                else _clean(report[camel])
            )

    return line


@csrf_exempt
def csp_report(request):
    """`POST /csp-report/`: apunta el informe en el log y contesta 204."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    if not csp_report_ip.consume(request):
        return HttpResponse(status=204)

    try:
        length = int(request.META.get('CONTENT_LENGTH') or 0)
    except ValueError:
        length = 0

    if length <= 0 or length > MAX_BODY_BYTES:
        return HttpResponse(status=204)

    try:
        payload = json.loads(request.body[:MAX_BODY_BYTES])
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=204)

    for report in _reports(payload):
        logger.warning('CSP report-only: %s', summarize(report))

    return HttpResponse(status=204)

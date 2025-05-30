#  apps/project/api/platform/insolvency_form/services/creditor_enricher.py

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Optional, Tuple

from django.db.models import Q

from ..models import AttlasInsolvencyCreditorsModel
from .chatgpt_api import ChatGPTAPI

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text)\
        .encode("ascii", "ignore")\
        .decode()\
        .upper().strip()

# ---------------------------------------------------------------------
#  1) BÚSQUEDA LOCAL
# ---------------------------------------------------------------------


def _find_in_local_db(creditor_name: str) -> tuple[Optional[str], Optional[str]]:
    norm = _normalize(creditor_name)

    # 1) Trae sólo los que ya tienen datos
    qs = (
        AttlasInsolvencyCreditorsModel.objects
        .exclude(Q(nit__isnull=True) | Q(nit=""))
        .exclude(Q(creditor_contact__isnull=True) | Q(creditor_contact=""))
        .order_by("-created")
    )

    # 2) Recorre en Python y compara los nombres normalizados
    for q in qs:
        if q.creditor and norm in _normalize(q.creditor):
            return (q.nit, q.creditor_contact)

    return (None, None)

# ---------------------------------------------------------------------
#  2) BÚSQUEDA CON IA (ChatGPT)
# ---------------------------------------------------------------------


_RE_JSON = re.compile(r"\{.*\}", re.S)


def creditor_nit_contact_prompt(self, creditor_name):
    prompt = f"""
    Eres un asistente jurídico colombiano.
    Cuando se te pida 'Dame el NIT y el correo de contacto de X',
    debes responder únicamente un JSON plano con las claves:
    'nit' (número de identificación tributaria) y 'contact' (correo electrónico).
    
    Instrucciones clave:
    - No incluyas explicaciones, descripciones ni texto adicional.
    - El JSON debe estar sin encabezados, sin ```json ni backticks, solo las llaves y el contenido.
    - Si conoces el correo de notificaciones judiciales de la entidad, usa ese. Si no, usa el correo general de contacto.
    - Para los siguientes bancos usa exactamente estos correos judiciales (sin intentar buscar otros):
      Bancolombia: notificacijudicial@bancolombia.com.co
      Banco de Bogotá: rjudicial@bancodebogota.com.co
      Banco Davivienda: notificacionesjudiciales@davivienda.com
      Banco Popular: notificacionesjudicialesvjuridica@bancopopular.com.co
      Banco BBVA: notifica.co@bbva.com
      Banco AV Villas: notificacionesjudiciales@bancoavvillas.com.co
      Banco Itaú: notificaciones.juridico@itau.co
      Banco Colpatria: notificbancolpatria@scotiabankcolpatria.com
      Banco BCSC: notificacionesjudiciales@fundaciongruposocial.co
      Banco Citibank: legalnotificacionescitibank@citi.com.co
      Banco Agrario de Colombia: notificacionesjudiciales@bancoagrario.gov.co
    
    Ejemplo de respuesta:
    {{
        "nit": "123456789",
        "contact": "notificaciones@empresa.com"
    }}
    """

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Dame el NIT y el correo de contacto de {creditor_name}."}
    ]

    model = "gpt-4o"
    temperature = 0

    return messages, model, temperature


def _find_via_chatgpt(creditor_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Pregunta a ChatGPT por el NIT y al menos un dato de contacto.
    Espera JSON plano: {"nit": "...", "contact": "..."}.
    """
    try:
        api = ChatGPTAPI()
        messages, model, temperature = creditor_nit_contact_prompt(creditor_name)
        response = api.get_response_json(model, messages, temperature)

        match = _RE_JSON.search(response)

        if not match:
            logger.warning(
                "Sin JSON reconocible en la respuesta: %r", response)
            return None, None

        data = json.loads(match.group())

        nit = data.get("nit")
        contact = data.get("contact")

        if nit or contact:
            return nit, contact

        return None, None

    except json.JSONDecodeError as exc:
        logger.error("ChatGPT JSON decode error - %s", exc, exc_info=True)
        return None, None

    except TypeError as exc:
        logger.error("ChatGPT JSON parse error - %s", exc, exc_info=True)
        return None, None

    except Exception as exc:
        logger.error("ChatGPT search failed - %s", exc, exc_info=True)
        return None, None

# ───────────────────────────────────────────────────────────────
# ORQUESTADOR ACUMULATIVO
# ───────────────────────────────────────────────────────────────


def enrich_creditor(name: str, *, nature_type: str | None = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Busca secuencialmente en las tres fuentes y va completando la
    información que falte.  Se detiene tan pronto obtiene *ambos*
    datos.  Al final puede devolver:
      * (nit, contact)        → ambos hallados
      * (nit, None)           → solo NIT
      * (None, contact)       → solo contacto
      * (None, None)          → nada encontrado
    """
    if nature_type == AttlasInsolvencyCreditorsModel.NATURE_OPTIONS.CP:
        return None, None

    nit: Optional[str] = None
    contact: Optional[str] = None

    for fn in (_find_in_local_db, _find_via_chatgpt):
        n, c = fn(name)
        nit = nit or n
        contact = contact or c
        if nit and contact:
            break

    return nit, contact

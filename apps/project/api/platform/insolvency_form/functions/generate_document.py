# apps\project\api\platform\insolvency_form\functions\generate_document.py

"""
Funciones utilitarias para construir y renderizar el documento DOCX
correspondiente a un AttlasInsolvencyFormModel.
Requiere: docxtpl==0.19.1, python-barcode[images], Pillow.
"""

import base64
import datetime
import logging
import os
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from barcode import Code128
from barcode.writer import ImageWriter
from django.db.models import Case, IntegerField, Value, When
from docx.shared import Cm
from docxtpl import DocxTemplate, InlineImage

from ..models import (AttlasInsolvencyAssetModel, AttlasInsolvencyFormModel,
                      AttlasInsolvencyIncomeModel,
                      AttlasInsolvencyIncomeOtherModel,
                      AttlasInsolvencyJudicialProcessModel,
                      AttlasInsolvencyResourceTableModel)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Helpers para imágenes
# --------------------------------------------------------------------------- #


def _barcode_bytes(data: str) -> BytesIO:
    """
    Genera un código de barras Code-128 en memoria.
    """
    buf = BytesIO()
    Code128(data, writer=ImageWriter()).write(buf)
    buf.seek(0)
    return buf


def process_image(doc: DocxTemplate, image_stream: BytesIO | bytes, width_cm: int = 10) -> InlineImage:
    """
    Convierte un stream de imagen en InlineImage para docxtpl.
    """
    if hasattr(image_stream, 'read'):
        data = image_stream.read()         # lee todo
        image_stream = BytesIO(data)
        image_stream.seek(0)
    elif isinstance(image_stream, bytes):
        image_stream = BytesIO(image_stream)
    # ahora es un BytesIO listo
    return InlineImage(doc, image_stream, width=Cm(width_cm))


# --------------------------------------------------------------------------- #
# Plantilla
# --------------------------------------------------------------------------- #
TEMPLATE_FILE = (
    Path(__file__).resolve().parent.parent /
    "templates" / "insolvency_template.docx"
)


def load_template(path: str | Path | None = None) -> DocxTemplate:
    """
    Devuelve la plantilla DocxTemplate ya cargada.
    """
    path = path or TEMPLATE_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(f"Plantilla no encontrada en: {path}")
    return DocxTemplate(path)


def _age(date_: datetime.date | None) -> int | None:
    if not date_:
        return None
    today = datetime.date.today()
    return today.year - date_.year - ((today.month, today.day) < (date_.month, date_.day))


def _build_debtor_partner(instance: AttlasInsolvencyFormModel) -> tuple[dict, dict]:
    """
    Construye el diccionario de datos del deudor para Jinja.
    """
    debtor_current_age = _age(instance.debtor_birth_date)

    debtor = {
        "document_number": instance.debtor_document_number,
        "document_expedition_city": instance.debtor_expedition_city,
        "first_name": instance.debtor_first_name,
        "last_name": instance.debtor_last_name,
        "is_merchant": " comerciante" if instance.debtor_is_merchant else " no comerciante",
        "phone": instance.debtor_cell_phone,
        "email": instance.debtor_email,
        "birth_date": instance.debtor_birth_date,
        "current_age": debtor_current_age,
        "address": instance.debtor_address,
        "sex": instance.debtor_sex,
        "cessation_report": instance.debtor_cessation_report,
    }

    partner = {
        "marital_status": instance.partner_marital_status,
        "document_number": instance.partner_document_number,
        "first_name": instance.partner_name,
        "last_name": instance.partner_last_name,
        "email": instance.partner_email,
        "phone": instance.partner_cell_phone,
        "relationship_duration": instance.partner_relationship_duration
    }

    return debtor, partner


def _build_creditors(instance: AttlasInsolvencyFormModel) -> list:
    """
    Serializa los acreedores para Jinja.
    """
    creditors = []
    total_capital = 0.0
    
    for c in instance.creditors_form.all().order_by("created"):
        capital = float(c.capital_value or 0)
        total_capital += capital
        creditors.append(
            {
                "creditor": c.creditor,
                "nit": c.nit,
                "creditor_contact": c.creditor_contact,
                "nature_type": c.nature_type,
                "other_nature": c.other_nature,
                "personal_consanguinity": c.personal_consanguinity,
                "personal_credit_interest_rate": float(c.personal_credit_interest_rate)
                if c.personal_credit_interest_rate
                else None,
                "guarantee": c.guarantee,
                "capital_value": float(c.capital_value or 0),
                "days_overdue": c.days_overdue,
                "credit_classification": c.credit_classification,
            }
        )
    return creditors, total_capital


def _build_creditors_unique(instance: AttlasInsolvencyFormModel) -> list:
    """
    Devuelve una lista de acreedores únicos, mostrando la versión más completa de cada uno.
    Prioriza registros que tengan tanto NIT como contacto, luego los que tengan NIT,
    y finalmente los que solo tienen nombre.
    """
    creditors_dict = {}  # Usaremos el nombre normalizado como clave

    for c in instance.creditors_form.all().order_by("created"):
        norm_creditor = (c.creditor or "").strip().lower()

        # Si es la primera vez que vemos este acreedor, lo agregamos directamente
        if norm_creditor not in creditors_dict:
            creditors_dict[norm_creditor] = {
                "creditor": c.creditor,
                "nit": c.nit,
                "creditor_contact": c.creditor_contact,
            }
        else:
            # Si ya existe, decidimos si actualizarlo con datos más completos
            existing = creditors_dict[norm_creditor]

            # Actualizamos NIT si el nuevo lo tiene y el existente no
            if not existing["nit"] and c.nit:
                existing["nit"] = c.nit

            # Actualizamos contacto si el nuevo lo tiene y el existente no
            if not existing["creditor_contact"] and c.creditor_contact:
                existing["creditor_contact"] = c.creditor_contact

    # Convertimos el diccionario a lista manteniendo solo los valores
    return list(creditors_dict.values())


def _build_incomes(instance: AttlasInsolvencyFormModel) -> list[dict]:
    """
    Serializa ingresos y sus 'others'.
    """
    incomes = []
    for income in instance.incomes.all():
        obj = {
            "type": income.type,
            "amount": float(income.amount or 0),
            "other_incomes": [],
        }
        if income.type == AttlasInsolvencyIncomeModel.IncomeType.OTHER:
            others = AttlasInsolvencyIncomeOtherModel.objects.filter(
                income=income)
            obj["other_incomes"] = [
                {"detail": o.detail, "amount": float(o.amount)} for o in others
            ]
        incomes.append(obj)
    return incomes


def _build_assets(instance: AttlasInsolvencyFormModel) -> list:
    qs = AttlasInsolvencyAssetModel.objects.filter(
        form=instance
    ).order_by(
        "created"
    )

    assets = [
        {
            "asset_type": a.asset_type,
            "name": a.name,
            "identification": a.identification,
            "lien": a.lien,
            "affectation": a.affectation,
            "legal_measure": a.legal_measure,
            "patrimonial_society": a.patrimonial_society,
            "commercial_value": float(a.commercial_value),
            "exclusion": a.exclusion,
        }
        for a in qs
    ]

    return assets


def _build_judicial_processes(instance: AttlasInsolvencyFormModel) -> list:
    qs = AttlasInsolvencyJudicialProcessModel.objects.filter(form=instance).order_by(
        "created"
    )

    processes = [
        {
            "affectation": p.affectation,
            "court": p.court,
            "description": p.description,
            "case_code": p.case_code,
            "status": p.process_status,
        }
        for p in qs
    ]

    return processes


def _build_resource_header(instance: AttlasInsolvencyFormModel) -> dict:
    if not instance.resources.exists():
        return {"has_food_obligation": False, "children_count": 0, "proposed_value": 0.0}
    r = instance.resources.first()

    resource_headers = {
        "has_food_obligation": r.has_food_obligation,
        "children_count": r.children_count,
        "proposed_monthly_value": float(r.proposed_monthly_value or 0),
    }

    return resource_headers


def _build_resource_tables(instance: AttlasInsolvencyFormModel) -> tuple[list, float]:
    """
    Serializa las tablas de recursos, ordenando de modo que
    la que tenga relationship == 'DEUDOR' quede siempre al inicio,
    y coloca 'relationship' como primer clave en el dict.
    """
    # Tomamos el primer recurso (normalmente hay uno por formulario)
    resource = instance.resources.first()
    if not resource:
        return [], 0.0

    # Anotamos is_deudor = 0 para DEUDOR, 1 para el resto, y ordenamos
    qs = (
        resource.tables
        .annotate(
            is_deudor=Case(
                When(relationship__iexact="DEUDOR", then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("is_deudor", "created")
    )

    tables: list[dict] = []
    total_global = Decimal("0")

    for t in qs:
        subtotal = Decimal("0")
        rows: list[dict] = []
        for it in t.items.all():
            val = Decimal(it.value or 0)
            subtotal += val
            rows.append({
                "label": it.label,
                "legal_support": it.legal_support,
                "value": float(val),
            })
        total_global += subtotal

        # Construimos el dict con 'relationship' en primer lugar
        tables.append({
            "relationship": t.relationship,
            "title": t.title,
            "disability": "Si" if t.disability else "No",
            "age": t.age,
            "gender": t.gender,
            "rows": rows,
            "subtotal": float(subtotal),
        })

    return tables, float(total_global)


def build_context(doc: DocxTemplate, instance: AttlasInsolvencyFormModel) -> dict:
    """
    Construye el diccionario de contexto para docxtpl.
    """
    debtor, partner = _build_debtor_partner(instance)
    creditors, total_capital = _build_creditors(instance)
    unique_creditors = _build_creditors_unique(instance)
    assets = _build_assets(instance)
    judicial = _build_judicial_processes(instance)
    incomes = _build_incomes(instance)
    resource_header = _build_resource_header(instance)
    tables, total_global = _build_resource_tables(instance)
    signature_inline = None

    # Firma del deudor (puede ser None)
    if instance.signature_form.exists():
        sig_obj = instance.signature_form.first()
        sig_str = sig_obj.signature or ""
        # Extraemos solo el payload base64 (quitamos cualquier prefijo data:...;base64,)
        if ',' in sig_str:
            b64_payload = sig_str.split(',', 1)[1]
        else:
            b64_payload = sig_str
        if b64_payload.strip():
            try:
                # Decodificamos el b64 y lo convertimos en InlineImage
                image_bytes = base64.b64decode(b64_payload)
                signature_inline = process_image(doc, image_bytes, width_cm=6)
            except Exception as e:
                logger.error(f"Error procesando la firma: {e}")

    # Código de barras con el UUID del formulario
    date_str = datetime.datetime.now().strftime("%d/%m/%Y")
    barcode_value = f"{instance.id}-{date_str}"
    barcode_inline = process_image(doc, _barcode_bytes(barcode_value), 6)

    form_data = {
        "form": instance.id,
        "debtor": debtor,
        "partner": partner,
        "creditors": creditors,
        "total_capital": total_capital,
        "unique_creditors": unique_creditors,
        "assets": assets,
        "judicial_processes": judicial,
        "incomes": incomes,
        "tables": tables,
        "total_global": total_global,
        **resource_header,
        "signature": signature_inline,
        "barcode": barcode_inline,
    }

    return form_data


def render_document(instance: AttlasInsolvencyFormModel, path=None) -> BytesIO:
    """Genera el DOCX en memoria y lo devuelve como BytesIO."""
    try:
        doc = load_template(path)
        context = build_context(doc, instance)
        doc.render(context)
        output = BytesIO()
        doc.save(output)
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error rendering document: {e}")
        raise

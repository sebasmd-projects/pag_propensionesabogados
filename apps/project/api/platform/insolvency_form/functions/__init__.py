import base64
import os
from datetime import datetime
from io import BytesIO

import unidecode
from barcode import Code128
from barcode.writer import ImageWriter
from docx.shared import Cm
from docxtpl import DocxTemplate, InlineImage


def generate_barcode_from_form_id(form_id, date=None):
    """Genera código de barras mejorado con manejo de errores"""
    try:
        date = date or datetime.now()
        code_text = f"{form_id} - {date.strftime('%d/%m/%Y')}"

        # Sanitizar texto y limitar longitud
        sanitized_text = unidecode.unidecode(code_text)
        sanitized_text = ''.join(
            c for c in sanitized_text if c.isalnum() or c in ('-', ' ', '/'))

        buffer = BytesIO()
        Code128(sanitized_text, writer=ImageWriter()).write(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error generando código de barras: {str(e)}")
        raise


def generate_barcode_base64(form_id, date=None):
    """Genera código de barras en base64 con manejo de errores"""
    try:
        buffer = generate_barcode_from_form_id(form_id, date)
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    except Exception as e:
        print(f"Error generando base64: {str(e)}")
        return ""


def format_currency(value):
    """Convierte el valor a float y lo formatea como moneda (string)"""
    try:
        num = float(str(value).replace('.', '').replace(',', '.'))
        return "${:,.2f}".format(num)
    except Exception:
        return "N/A"


def load_template(template_path):
    """Carga la plantilla con validación"""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Plantilla no encontrada en: {template_path}")

    return DocxTemplate(template_path)


def process_image(doc, image_data, default_width=10):
    try:
        if not image_data or ';base64,' not in image_data:
            return None

        # Extraer el tipo MIME y los datos base64
        header, encoded = image_data.split(';base64,', 1)
        image_type = header.split('/')[-1]

        # Decodificar base64
        decoded = base64.b64decode(encoded)
        buffer = BytesIO(decoded)

        return InlineImage(doc, buffer, width=Cm(default_width))

    except Exception as e:
        print(f"Error procesando imagen: {str(e)}")
        return None


def parse_number(value):
    try:
        return float(str(value).replace('.', '').replace(',', '.'))
    except Exception:
        return 0.0


def marital_status_text(value):
    if value == 'spouse':
        return "Cónyuge"
    if value == 'marital_declaration':
        return "Declaración de unión marital de hecho"
    if value == 'free_union':
        return "Unión libre"
    if value == 'not_applicable':
        return "No aplica"


def asset_type_text(value):
    if value == 'Furniture':
        return "Mueble"
    if value == 'Real Estate':
        return "Inmueble"


def build_context(doc, instance, form_data):
    """Construye el contexto para la plantilla, formateando los valores monetarios y calculando el total global."""
    barcode_buffer = generate_barcode_from_form_id(
        instance["id"], instance["created"])
    barcode_image = InlineImage(doc, barcode_buffer, width=Cm(6))
    support_docs = []

    is_merchant = form_data.get("is_merchant", "no")

    tables = [{
        **table,
        "table_items": [
            {
                **item,
                "value_num": parse_number(item.get("value", "0")),
                "value": format_currency(item.get("value", "0"))
            }
            for item in table.get("items", [])
        ]
    } for table in form_data.get("tables", [])]

    total_global = 0
    for table in tables:
        total_global += sum(item["value_num"] for item in table["table_items"])

    for doc_item in form_data.get("supportDocs", []):
        image = process_image(doc, doc_item.get("file"))
        if image:
            support_docs.append({
                "description": doc_item.get("description", ""),
                "file": image
            })

    context = {
        "barcode": barcode_image,
        "first_name": form_data.get("first_name", ""),
        "last_name": form_data.get("last_name", ""),
        "document_number": form_data.get("document_number", ""),
        "is_merchant": "comerciante" if is_merchant == "yes" else "NO comerciante",
        "assets": [{
            **asset,
            "commercial_value_formatted": format_currency(asset.get("commercial_value", "0")),
            "commercial_value_num": parse_number(asset.get("commercial_value", "0")),
            "asset_type": asset_type_text(asset.get("asset_type", "not_applicable")),
        } for asset in form_data.get("assets", [])],
        "creditors": [{
            **creditor,
            "capital_value_formatted": format_currency(creditor.get("capital_value", "0")),
            "capital_value_num": parse_number(creditor.get("capital_value", "0"))
        } for creditor in form_data.get("creditors", [])],
        "tables": tables,
        "proposedMonthlyValue_formatted": format_currency(form_data.get("proposedMonthlyValue", 0)),
        "total_global": format_currency(total_global/10),
        "marital_status_display": marital_status_text(form_data.get("marital_status", "not_applicable")),
        "marital_status_raw": form_data.get("marital_status", "not_applicable"),
        **{k: v for k, v in form_data.items() if k not in ['assets', 'creditors', 'tables', 'proposedMonthlyValue']},
    }

    context.update({
        "signature": process_image(doc, form_data.get("signature")),
        "cedulaFront": process_image(doc, form_data.get("cedulaFront")),
        "cedulaBack": process_image(doc, form_data.get("cedulaBack")),
        "supportDocs": support_docs
    })

    return context

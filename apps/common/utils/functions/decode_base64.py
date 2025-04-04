import base64
from io import BytesIO
from docxtpl import InlineImage
from docx.shared import Cm


def decode_base64_image(data_base64, doc_tpl, width_cm=5):
    try:
        if "," in data_base64:
            header, base64_data = data_base64.split(",", 1)
        else:
            base64_data = data_base64

        image_bytes = base64.b64decode(base64_data)
        image_stream = BytesIO(image_bytes)

        # Retornar imagen para docxtpl
        return InlineImage(doc_tpl, image_stream, width=Cm(width_cm))
    except Exception as e:
        print("Error procesando imagen base64:", e)
        return "No img"

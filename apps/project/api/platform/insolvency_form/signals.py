import os
import traceback

from django.conf import settings
from django.core.mail import EmailMessage
from .functions import load_template, build_context


def send_insolvency_email(sender, instance, created, **kwargs):
    """
    Signal para enviar el documento de insolvencia por correo
    cada vez que se crea (o actualiza) un formulario de insolvencia.
    """
    try:
        # Si solo deseas enviar el correo cuando se crea el objeto, descomenta:
        if not created:
            return

        form_data = instance.form_data or {}
        if not form_data:
            return

        # 1) Cargar la plantilla .docx
        template_path = os.path.join(
            settings.BASE_DIR,
            'apps', 'project', 'api', 'platform', 'insolvency_form', 'templates',
            'insolvency_template.docx'
        )
        doc = load_template(template_path)

        # 2) Construir contexto (basado en tu build_context del archivo generar_manualmente.py)
        #    Ten en cuenta que aquí tomamos 'instance' como un dict parcial.
        instance_dict = {
            "id": str(instance.id),
            "created": instance.created
        }
        context = build_context(
            doc, instance_dict, form_data)

        # 3) Renderizar el documento con el contexto
        doc.render(context)

        # 4) Guardar el documento en un archivo temporal (o en la carpeta que desees)
        #    Ajusta la ruta donde se quiera guardar el archivo.
        first_name = form_data.get("first_name", "")
        last_name = form_data.get("last_name", "")
        document_number = form_data.get("document_number", "")
        form_id = str(instance.id)

        output_filename = f"Formulario_Insolvencia_{first_name}_{last_name}_{document_number}_{form_id}.docx"
        output_path = os.path.join(
            settings.BASE_DIR, 'public', 'media', 'insolvency', 'documents', output_filename
        )
        doc.save(output_path)

        # 5) Preparar y enviar el correo con el archivo adjunto
        subject = f"Documento de Insolvencia | {first_name} {last_name}"
        body = (
            f"Se adjunta el documento de insolvencia de la persona "
            f"{first_name} {last_name} - {document_number} - {form_id}."
        )

        from_email = settings.DEFAULT_FROM_EMAIL
        # Ajusta el correo de destino
        to_email = ['insolvencia@propensionesabogados.com']

        email_msg = EmailMessage(subject, body, from_email, to_email)
        with open(output_path, 'rb') as f:
            email_msg.attach(
                output_filename,
                f.read(),
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

        email_msg.send()

        # 6) Actualizar estado de envío en la instancia
        instance.email_sent = True
        instance.email_error = ""
        instance.save()

        # 7) (Opcional) Borrar el archivo temporal
        os.remove(output_path)

    except Exception as e:
        # Manejo de errores y guardado del error en la instancia
        instance.email_sent = False
        instance.email_error = traceback.format_exc()
        instance.save()

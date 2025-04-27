# apps\project\api\platform\insolvency_form\signals.py

import traceback

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .functions import enrich_creditor, render_document
from .models import AttlasInsolvencyCreditorsModel, AttlasInsolvencyFormModel


@receiver(pre_save, sender=AttlasInsolvencyCreditorsModel)
def save_nit_and_contact(sender, instance, **kwargs):
    if instance.nature_type == sender.NATURE_OPTIONS.CP:
        return

    nit, contact = enrich_creditor(
        instance.creditor,
        nature_type=instance.nature_type,
    )
    if nit and not instance.nit:
        instance.nit = nit
    if contact and not instance.creditor_contact:
        instance.creditor_contact = contact


@receiver(post_save, sender=AttlasInsolvencyFormModel)
def send_insolvency_email(sender, instance: AttlasInsolvencyFormModel, created, **kwargs):
    """
    Envía el documento por correo al crearse el formulario Y cuando
    se marca como completado, evitando duplicados.
    """
    should_send = (
        created or instance.is_completed) and not instance.email_sent
    
    if not should_send or settings.DEBUG:
        return

    try:
        attachment = render_document(instance)

        email = EmailMessage(
            subject=f"Attlas | Solicitud de insolvencia {instance.debtor_first_name} {instance.debtor_last_name} - {instance.debtor_document_number}",
            body=(
                "Adjunto encontrarás el documento generado automáticamente desde la plataforma de insolvencia.\n\n"
                f"{instance.debtor_first_name} {instance.debtor_last_name} - {instance.debtor_document_number}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=["insolvencia@propensionesabogados.com"],
        )
        email.attach(
            filename=f"{instance.debtor_document_number}_insolvencia.docx",
            content=attachment.getvalue(),
            mimetype=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml."
                "document"
            ),
        )
        email.send(fail_silently=False)

        instance.email_sent = True
        instance.email_error = ""
    except Exception:
        instance.email_sent = False
        instance.email_error = traceback.format_exc()

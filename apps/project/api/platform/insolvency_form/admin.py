import json
import os

from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.mail import EmailMessage
from django.db import models
from django.utils.translation import gettext_lazy as _

from .functions import build_context, load_template
from .models import AttlasInsolvencyFormModel


class JSONPrettyTextarea(forms.Textarea):
    def format_value(self, value):
        if isinstance(value, dict):
            return json.dumps(value, indent=4, ensure_ascii=False)
        return value


@admin.register(AttlasInsolvencyFormModel)
class AttlasInsolvencyFormAdmin(admin.ModelAdmin):
    actions = ['reenviar_correo']

    list_display = ('id', 'user', 'email_sent', 'created', 'updated')

    readonly_fields = (
        'id', 'user', 'email_sent',
        'email_error', 'created', 'updated',
    )

    fieldsets = (
        (_('Information'), {
            'fields': ('id', 'user', 'form_data',)
        }),
        (_('Email'), {
            'fields': ('email_sent', 'email_error',)
        }),
        (_('Other'), {
            'fields': ('default_order', 'is_active', 'created', 'updated',),
            'classes': ('collapse',)
        }),
    )

    formfield_overrides = {
        models.JSONField: {'widget': JSONPrettyTextarea(attrs={'cols': 120, 'rows': 30})},
    }

    @admin.action(description='Reenviar correo con el documento')
    def reenviar_correo(self, request, queryset):
        """
        Acción de Admin para regenerar el documento y reenviar el correo
        seleccionado manualmente.
        """
        for instance in queryset:
            try:
                form_data = instance.form_data or {}
                if not form_data:
                    continue

                # 1) Cargar la plantilla .docx
                template_path = os.path.join(
                    settings.BASE_DIR,
                    'apps', 'project', 'api', 'platform', 'insolvency_form', 'templates',
                    'insolvency_template.docx'
                )
                doc = load_template(template_path)

                # 2) Construir contexto
                instance_dict = {
                    "id": str(instance.id),
                    "created": instance.created
                }
                context = build_context(doc, instance_dict, form_data)

                # 3) Renderizar
                doc.render(context)

                # 4) Guardar archivo
                first_name = form_data.get("first_name", "")
                last_name = form_data.get("last_name", "")
                document_number = form_data.get("document_number", "")
                form_id = str(instance.id)

                output_filename = f"Formulario_Insolvencia_{first_name}_{last_name}_{document_number}_{form_id}.docx"
                output_path = os.path.join(
                    settings.BASE_DIR, 'public', 'media', 'insolvency', 'documents', output_filename
                )

                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                doc.save(output_path)

                # 5) Preparar y enviar el correo
                subject = f"Documento de Insolvencia | {first_name} {last_name}"
                body = (
                    f"Se adjunta el documento de insolvencia de la persona "
                    f"{first_name} {last_name} - {document_number} - {form_id}."
                )
                from_email = settings.DEFAULT_FROM_EMAIL
                # Ajusta destinatario
                to_email = ['insolvencia@propensionesabogados.com']

                email_msg = EmailMessage(subject, body, from_email, to_email)
                with open(output_path, 'rb') as f:
                    email_msg.attach(
                        output_filename,
                        f.read(),
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    )
                email_msg.send()

                # 6) Actualizar estado en la instancia
                instance.email_sent = True
                instance.email_error = ""
                instance.save()

                # 7) Eliminar archivo temporal (opcional)
                os.remove(output_path)

            except Exception as e:
                instance.email_sent = False
                instance.email_error = str(e)
                instance.save()

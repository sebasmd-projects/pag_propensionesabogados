# apps\project\api\platform\insolvency_form\admin.py
import os

import nested_admin
from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.mail import EmailMessage
from django.utils.translation import gettext_lazy as _

from .functions import build_context, load_template
from .models import (AttlasInsolvencyAssetModel,
                     AttlasInsolvencyCreditorsModel, AttlasInsolvencyFormModel,
                     AttlasInsolvencyIncomeModel,
                     AttlasInsolvencyIncomeOtherModel,
                     AttlasInsolvencyJudicialProcessModel,
                     AttlasInsolvencyResourceItemModel,
                     AttlasInsolvencyResourceModel,
                     AttlasInsolvencyResourceTableModel,
                     AttlasInsolvencySignatureModel)
from .widgets import Base64SignatureWidget


class SignatureForm(forms.ModelForm):
    class Meta:
        model = AttlasInsolvencySignatureModel
        fields = '__all__'
        widgets = {
            'signature': Base64SignatureWidget(attrs={
                'rows': 4,
                'cols': 100,
                # 'style': 'display: none;'
            })
        }


class GeneralInline(nested_admin.NestedStackedInline):
    extra = 0
    exclude = ('is_active', 'created', 'updated', 'language', 'default_order')


class CreditorsInline(GeneralInline):
    model = AttlasInsolvencyCreditorsModel
    fk_name = 'form'


class IncomeOtherInline(GeneralInline):
    model = AttlasInsolvencyIncomeOtherModel
    fk_name = 'income'


class IncomeInline(GeneralInline):
    model = AttlasInsolvencyIncomeModel
    fk_name = 'form'
    inlines = [IncomeOtherInline]


class ResourceItemInline(GeneralInline):
    model = AttlasInsolvencyResourceItemModel
    fk_name = 'table'


class ResourceTableInline(GeneralInline):
    model = AttlasInsolvencyResourceTableModel
    fk_name = 'resource'
    inlines = [ResourceItemInline]


class ResourceInline(GeneralInline):
    model = AttlasInsolvencyResourceModel
    fk_name = 'form'
    inlines = [ResourceTableInline]


class AssetInline(GeneralInline):
    model = AttlasInsolvencyAssetModel
    fk_name = 'form'


class JudicialProcessInline(GeneralInline):
    model = AttlasInsolvencyJudicialProcessModel
    fk_name = 'form'


class SignatureInline(GeneralInline):
    model = AttlasInsolvencySignatureModel
    form = SignatureForm
    max_num = 1
    fk_name = 'form'


@admin.register(AttlasInsolvencyFormModel)
class AttlasInsolvencyFormAdmin(nested_admin.NestedModelAdmin):
    list_display = (
        'id',
        'created',
        'user',
        'current_step',
        'is_completed',
        'email_sent',
        'email_error',
    )
    list_filter = (
        'current_step',
        'is_completed',
        'email_sent',
    )
    search_fields = (
        'debtor_document_number',
        'debtor_first_name',
        'debtor_last_name',
        'debtor_cell_phone',
        'debtor_email',
    )
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'id',
                    'user',
                ),
            }
        ),
        (
            _('1. Legal requirements'),
            {
                'fields': (
                    'accept_legal_requirements',
                    'accept_terms_and_conditions'
                ),
            }
        ),
        (
            _('2. Personal data'),
            {
                'fields': (
                    'debtor_document_number',
                    'debtor_expedition_city',
                    'debtor_first_name',
                    'debtor_last_name',
                    'debtor_is_merchant',
                    'debtor_cell_phone',
                    'debtor_email',
                    'debtor_birth_date',
                    'debtor_address',
                ),
            }
        ),
        (
            _('3. Cessation of payments Statement'),
            {
                'fields': (
                    'debtor_statement_accepted',
                ),
            }
        ),
        (
            _('4. Cessation of payments Report'),
            {
                'fields': (
                    'debtor_cessation_report',
                ),
            }
        ),
        (
            _('9. Partner data'),
            {
                'fields': (
                    'partner_marital_status',
                    'partner_document_number',
                    'partner_name',
                    'partner_last_name',
                    'partner_email',
                    'partner_cell_phone',
                    'partner_relationship_duration'
                ),
            }
        ),
        (
            _('Status'),
            {
                'fields': (
                    'current_step',
                    'is_completed',
                    'email_sent',
                    'email_error',
                    'is_active',
                ),
            }
        ),
        (
            _('Stamped Times'),
            {
                'fields': (
                    'created',
                    'updated'
                ),
            }
        )
    )

    readonly_fields = (
        'id',
        'created',
        'updated',
        'user',
        'current_step',
        'is_completed',
        'email_sent',
        'email_error',
    )

    inlines = [
        CreditorsInline,
        AssetInline,
        JudicialProcessInline,
        IncomeInline,
        ResourceInline,
        SignatureInline,
    ]

    actions = ['reenviar_correo']

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


other_models = [
    AttlasInsolvencyAssetModel,
    AttlasInsolvencyCreditorsModel,
    AttlasInsolvencyIncomeModel,
    AttlasInsolvencyIncomeOtherModel,
    AttlasInsolvencyJudicialProcessModel,
    AttlasInsolvencyResourceItemModel,
    AttlasInsolvencyResourceModel,
    AttlasInsolvencyResourceTableModel,
    AttlasInsolvencySignatureModel
]

for model in other_models:
    admin.site.register(model, admin.ModelAdmin)

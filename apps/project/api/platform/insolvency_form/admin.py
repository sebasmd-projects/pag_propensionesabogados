# apps\project\api\platform\insolvency_form\admin.py
import json
import os

import nested_admin
from django import forms
from django.contrib import admin, messages
from django.core.mail import EmailMessage
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ImportExportActionModelAdmin
from django.conf import settings
from pathlib import Path

from .functions import render_document
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


class FormResource(resources.ModelResource):
    # campos básicos del form
    id = fields.Field(column_name='form_id', attribute='id')
    user = fields.Field(column_name='user_id', attribute='user__id')
    current_step = fields.Field(
        column_name='current_step', attribute='current_step')
    is_completed = fields.Field(
        column_name='is_completed', attribute='is_completed')
    created = fields.Field(column_name='created', attribute='created')
    updated = fields.Field(column_name='updated', attribute='updated')

    # inline / nested: los serializamos como JSON para no perder estructura
    creditors = fields.Field(column_name='creditors_json')
    assets = fields.Field(column_name='assets_json')
    judicial_processes = fields.Field(column_name='judicial_processes_json')
    incomes = fields.Field(column_name='incomes_json')
    resources = fields.Field(column_name='resources_json')
    signature = fields.Field(column_name='signature_b64')

    def dehydrate_creditors(self, form):
        qs = form.creditors_form.all().values(
            'creditor', 'nit', 'creditor_contact', 'nature_type', 'other_nature',
            'capital_value', 'days_overdue'
        )
        return json.dumps(list(qs), ensure_ascii=False, default=str)

    def dehydrate_assets(self, form):
        qs = form.asset_form.all().values(
            'asset_type', 'name', 'identification', 'lien', 'affectation',
            'legal_measure', 'patrimonial_society', 'commercial_value', 'exclusion'
        )
        return json.dumps(list(qs), ensure_ascii=False, default=str)

    def dehydrate_judicial_processes(self, form):
        qs = form.judicial_form.all().values(
            'affectation', 'court', 'description', 'case_code', 'process_status'
        )
        return json.dumps(list(qs), ensure_ascii=False, default=str)

    def dehydrate_incomes(self, form):
        out = []
        for inc in form.incomes.all():
            others = list(
                inc.incomeother_income.all().values('detail', 'amount')
            )
            out.append({
                'type': inc.type,
                'amount': inc.amount,
                'others': others
            })
        return json.dumps(out, ensure_ascii=False, default=str)

    def dehydrate_resources(self, form):
        out = []
        for r in form.resources.all():
            tables = []
            for t in r.tables.all():
                items = list(
                    t.items.all().values('label', 'legal_support', 'value')
                )
                tables.append({
                    'title': t.title,
                    'relationship': t.relationship,
                    'disability': t.disability,
                    'age': t.age,
                    'gender': t.gender,
                    'items': items
                })
            out.append({
                'has_food_obligation': r.has_food_obligation,
                'proposed_monthly_value': r.proposed_monthly_value,
                'children_count': r.children_count,
                'tables': tables
            })
        return json.dumps(out, ensure_ascii=False, default=str)

    def dehydrate_signature(self, form):
        sig = form.signature_form.first()
        return sig.signature if sig else ''

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = (
            'id', 'user', 'current_step', 'is_completed', 'created', 'updated',
            'creditors', 'assets', 'judicial_processes', 'incomes', 'resources', 'signature'
        )


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
class AttlasInsolvencyFormAdmin(nested_admin.NestedModelAdmin, ImportExportActionModelAdmin):
    resource_class = FormResource

    list_display = (
        'id',
        'user',
        'created',
        'updated',
        'current_step',
        'is_completed',
        'email_sent',
    )
    list_filter = (
        'current_step',
        'is_completed',
        'email_sent',
        'debtor_is_merchant'
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
                    'debtor_sex'
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

    actions = ['reenviar_correo', 'reenviar_correo_patrimonial']

    @admin.action(description="Reenviar correo con el documento")
    def reenviar_correo(self, request, queryset):
        ok, fail = 0, 0
        for instance in queryset:
            try:
                doc_file = render_document(instance)
                email = EmailMessage(
                    subject=f"ADMIN | Attlas | Solicitud de insolvencia {instance.debtor_first_name} {instance.debtor_last_name} - {instance.debtor_document_number}",
                    body=(
                        "Adjunto encontrarás el documento generado automáticamente desde la plataforma de insolvencia.\n\n"
                        f"{instance.debtor_first_name} {instance.debtor_last_name} - {instance.debtor_document_number}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=["insolvencia@propensionesabogados.com"],
                )
                email.attach(
                    f"{instance.debtor_first_name} {instance.debtor_last_name} - {instance.debtor_document_number}_insolvencia.docx",
                    doc_file.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                email.send(fail_silently=False)
                ok += 1
            except Exception as exc:
                self.message_user(
                    request,
                    f"Error al enviar {instance}: {exc}",
                    level=messages.ERROR,
                )
                fail += 1
        if ok:
            self.message_user(
                request,
                f"Documento reenviado correctamente para {ok} registro(s).",
                level=messages.SUCCESS,
            )
        if fail and not ok:
            self.message_user(
                request,
                "Ningún documento pudo ser reenviado.",
                level=messages.ERROR,
            )

    @admin.action(description="Reenviar correo con el documento - PATRIMONIOAL")
    def reenviar_correo_patrimonial(self, request, queryset):
        TEMPLATE_FILE = (
            Path(__file__).resolve().parent /
            "templates" / "insolvency_template_no_assets.docx"
        )

        ok, fail = 0, 0
        for instance in queryset:
            try:
                doc_file = render_document(
                    instance, path=TEMPLATE_FILE
                )
                email = EmailMessage(
                    subject=f"ADMIN | Attlas | Solicitud de insolvencia patrimonial {instance.debtor_first_name} {instance.debtor_last_name} - {instance.debtor_document_number}",
                    body=(
                        "Adjunto encontrarás el documento de insolvencia patrimonial generado automáticamente desde la plataforma de insolvencia.\n\n"
                        f"{instance.debtor_first_name} {instance.debtor_last_name} - {instance.debtor_document_number}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=["insolvencia@propensionesabogados.com"],
                )
                email.attach(
                    f"{instance.debtor_first_name} {instance.debtor_last_name} - {instance.debtor_document_number}_insolvencia_patrimonial.docx",
                    doc_file.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                email.send(fail_silently=False)
                ok += 1
            except Exception as exc:
                self.message_user(
                    request,
                    f"Error al enviar {instance}: {exc}",
                    level=messages.ERROR,
                )
                fail += 1
        if ok:
            self.message_user(
                request,
                f"Documento reenviado correctamente para {ok} registro(s).",
                level=messages.SUCCESS,
            )
        if fail and not ok:
            self.message_user(
                request,
                "Ningún documento pudo ser reenviado.",
                level=messages.ERROR,
            )


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

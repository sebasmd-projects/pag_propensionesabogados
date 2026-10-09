"""
El gestor dentro del admin de Django.

Por que el admin y no una pantalla propia
-----------------------------------------
El panel que habia era una pantalla propia, y ahi estaba el problema: tenia
que resolver por su cuenta la sesion, la contrasena, los permisos y el
registro de quien cambio que. Los resolvio mal --usuario fijo, contrasena en
el HTML, todo en el navegador-- porque son cuatro problemas dificiles y no
eran el encargo.

El admin ya los trae resueltos, y ademas trae `auditlog` enganchado a los tres
modelos. Lo que la cotizacion pide para esta parte es literalmente
«autenticacion y control de acceso mediante el sistema de seguridad del
framework»: esto es eso.

Lo que **no** esta aqui, y esta fuera del alcance contratado: tablas con
filtros y paginacion propias, exportacion segmentada, papelera, asignacion de
responsable y reportes gerenciales historicos.
"""

import os

from django.contrib import admin
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .access import can_use_case_manager
from . import paz_y_salvo
from .models import (CaseFinanceModel, CaseModel, ClientModel,
                     PazYSalvoDocumentModel)


class CaseManagerAdminMixin:
    """
    La misma puerta que `GestorRequiredMixin`, para el admin.

    El admin pregunta por permisos de Django; el gestor se reparte por grupo.
    Esto traduce lo uno a lo otro para que **haya una sola definicion** de
    quien entra, en `access.can_use_case_manager()`.
    """

    def has_view_permission(self, request, obj=None):
        return can_use_case_manager(request.user)

    def has_add_permission(self, request, obj=None):
        """
        `obj` lleva valor por defecto porque este mixin lo comparten un
        `ModelAdmin` y un `InlineModelAdmin`, y Django los llama distinto:

            ModelAdmin.has_add_permission(self, request)
            InlineModelAdmin.has_add_permission(self, request, obj)

        Con la firma del `ModelAdmin` a secas, abrir la ficha de un asunto
        --que lleva el inline del dinero-- reventaba con un `TypeError`.
        """
        return can_use_case_manager(request.user)

    def has_change_permission(self, request, obj=None):
        return can_use_case_manager(request.user)

    def has_delete_permission(self, request, obj=None):
        # Borrar un cliente se lleva por delante sus casos y su dinero, y no
        # hay papelera --esta fuera del alcance--. Se retira la vigencia.
        return request.user.is_superuser

    def has_module_permission(self, request):
        return can_use_case_manager(request.user)


class CaseFinanceInline(CaseManagerAdminMixin, admin.StackedInline):
    """
    El dinero, pegado a su caso.

    Va como `inline` y no como una entrada suelta del menu porque un importe
    sin su caso delante no se puede revisar: el saldo solo significa algo
    junto al esquema de honorarios.
    """

    model = CaseFinanceModel
    can_delete = False
    extra = 0
    readonly_fields = ('balance_display', 'expectation_display')
    fieldsets = (
        (None, {
            'fields': ('start_date', 'mandate', 'show_in_dashboard'),
        }),
        (_('Contingency'), {
            'fields': ('contingency_percentage', 'contingency_value'),
            'description': _(
                'A 0 % contingency is not a contingency: it is a closed fixed '
                'value, and it counts as debt, not as an expectation.'
            ),
        }),
        (_('Fixed fees (installments)'), {
            'fields': ('agreed_fee', 'paid_amount'),
        }),
        (_('Calculated'), {
            'fields': ('balance_display', 'expectation_display'),
            'description': _(
                'These are not stored: they are derived from the fields above.'
            ),
        }),
    )

    @admin.display(description=_('balance'))
    def balance_display(self, obj):
        return f'$ {obj.balance:,.0f}'.replace(',', '.') if obj.pk else '—'

    @admin.display(description=_('expectation'))
    def expectation_display(self, obj):
        return f'$ {obj.expectation:,.0f}'.replace(',', '.') if obj.pk else '—'


class DeletedFilter(admin.SimpleListFilter):
    title = _('Eliminados')
    parameter_name = 'deleted'

    def lookups(self, request, model_admin):
        return [('yes', _('Sí')), ('no', _('No'))]

    def queryset(self, request, queryset):
        if self.value() in ('yes', 'no'):
            return queryset.filter(deleted_at__isnull=self.value() == 'no')
        return queryset


class SoftDeleteAdminMixin:
    actions = ['restore_selected']

    def get_queryset(self, request):
        return self.model.all_objects.all()

    @admin.action(description=_('Restaurar'))
    def restore_selected(self, request, queryset):
        with transaction.atomic():
            for obj in queryset.select_for_update().filter(deleted_at__isnull=False):
                obj.restore()
        self.message_user(request, _('Registros restaurados. La vigencia no se reactiva automáticamente.'))

    def delete_model(self, request, obj):
        obj.soft_delete(request.user)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for obj in queryset.select_for_update():
                obj.soft_delete(request.user)


@admin.register(CaseModel)
class CaseAdmin(SoftDeleteAdminMixin, CaseManagerAdminMixin, admin.ModelAdmin):
    inlines = [CaseFinanceInline]
    list_display = (
        'client', 'service', 'stage', 'is_active',
        'paz_y_salvo_authorized', 'updated',
    )
    list_filter = (DeletedFilter, 'service', 'procedure', 'area', 'stage', 'is_active')
    search_fields = (
        'client__identification', 'client__full_name', 'case_number',
        'administrative_case_number', 'police_case_number',
    )
    autocomplete_fields = ('client',)
    readonly_fields = ('created', 'updated')
    fieldsets = (
        (None, {
            'fields': (
                'client', 'service', 'procedure', 'area', 'subtype',
                'second_subtype', 'service_other', 'procedure_other', 'area_other',
                'subtype_other', 'second_subtype_other', 'stage', 'instance', 'is_active',
            ),
        }),
        (_('Ordinary process'), {
            'fields': ('case_number', 'court', 'city'),
            'classes': ('collapse',),
        }),
        (_('Administrative procedure'), {
            'fields': (
                'sector', 'entity', 'administrative_case_number',
                'administrative_city',
            ),
            'classes': ('collapse',),
        }),
        (_('Police complaint'), {
            'fields': (
                'police_instance', 'police_office', 'police_case_number',
                'police_city',
            ),
            'classes': ('collapse',),
        }),
        (_('Settlement letter'), {
            'fields': ('paz_y_salvo_authorized',),
            'description': _(
                'While this is off the client cannot print the settlement '
                'letter, and the link does not even appear on the portal.'
            ),
        }),
        (_('Dates'), {
            'fields': ('created', 'updated'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Marcar o desmarcar el paz y salvo aqui es autorizarlo o retirarlo
        igual que en el gestor: crea o revoca su documento certificado.
        """
        was_authorized = bool(
            change and CaseModel.all_objects.filter(
                pk=obj.pk, paz_y_salvo_authorized=True).exists()
        )
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            paz_y_salvo.sync_authorization(obj, was_authorized)


@admin.register(PazYSalvoDocumentModel)
class PazYSalvoDocumentAdmin(CaseManagerAdminMixin, admin.ModelAdmin):
    """Solo lectura: el estado lo lleva la certificacion (en linea, con el comando como respaldo), no una mano."""

    list_display = (
        'short_case_id', 'status', 'authorized_at', 'gea_code', 'attempts',
        'certified_at',
    )
    list_filter = ('status',)
    search_fields = ('case__id', 'gea_code', 'gea_document_id')
    ordering = ('-authorized_at',)

    #: Los ficheros viven en `PrivateMediaStorage`, que no tiene URL: el admin
    #: de solo lectura pintaria `<a href=value.url>` y reventaria con un 500.
    #: Se sustituyen por estos metodos, que no piden nunca `.url`.
    file_fields = {
        'source_file': 'source_file_display',
        'public_copy_file': 'public_copy_file_display',
    }

    def get_readonly_fields(self, request, obj=None):
        return [
            self.file_fields.get(field.name, field.name)
            for field in self.model._meta.fields
        ]

    def get_fields(self, request, obj=None):
        # Sin permiso de cambio el admin vuelve de solo lectura todo lo que
        # hay en los fieldsets: si ahi siguen los FileField, vuelve el 500.
        return self.get_readonly_fields(request, obj)

    @admin.display(
        description=PazYSalvoDocumentModel._meta.get_field(
            'source_file').verbose_name)
    def source_file_display(self, obj):
        """Solo el nombre: es el original interno, sin enlace."""
        if not obj.source_file:
            return self.get_empty_value_display()
        return os.path.basename(obj.source_file.name)

    @admin.display(
        description=PazYSalvoDocumentModel._meta.get_field(
            'public_copy_file').verbose_name)
    def public_copy_file_display(self, obj):
        """
        El nombre del fichero y, si es el que sirve la descarga, su enlace.

        La descarga solo entrega el ultimo documento certificado de un caso
        con el paz y salvo autorizado; de cualquier otro (revocado, fallido,
        anterior) se ensena solo el nombre.
        """
        if not obj.public_copy_file:
            return self.get_empty_value_display()

        name = os.path.basename(obj.public_copy_file.name)
        served = PazYSalvoDocumentModel.objects.filter(
            case_id=obj.case_id,
            status=PazYSalvoDocumentModel.Status.CERTIFIED,
            case__paz_y_salvo_authorized=True,
        ).exclude(public_copy_file='').order_by('-authorized_at').first()

        if served is None or served.pk != obj.pk:
            return name

        return format_html(
            '<a href="{}">{}</a>',
            reverse('case_manager:paz_y_salvo_download', args=[obj.case_id]),
            name,
        )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientModel)
class ClientAdmin(SoftDeleteAdminMixin, CaseManagerAdminMixin, admin.ModelAdmin):
    list_display = (
        'document', 'full_name', 'email', 'is_active', 'code_state',
    )
    list_filter = (DeletedFilter, 'identification_type', 'is_active')
    search_fields = (
        'identification', 'full_name', 'email', 'legal_rep_name',
        'legal_rep_identification',
    )
    readonly_fields = ('code_state', 'created', 'updated')
    fields = (
        'identification_type', 'identification', 'verification_digit',
        'full_name', 'email', 'phone', 'legal_rep_name',
        'legal_rep_identification_type', 'legal_rep_identification',
        'legal_rep_email', 'legal_rep_phone', 'is_active',
        'code_state', 'created', 'updated',
    )

    @admin.display(description=_('identification'), ordering='identification')
    def document(self, obj):
        return obj.display_identification

    @admin.display(description=_('access codes'))
    def code_state(self, obj):
        """
        Por donde va la escalera de reenvios de ese cliente.

        Se ensena porque es lo primero que hay que mirar cuando alguien llama
        diciendo que no le llega el codigo: o no tiene correo registrado, o se
        quedo sin reenvios y esta esperando la hora.

        El codigo en si **no** se ensena, ni aqui ni en ningun sitio: solo se
        guarda su HMAC, y solo en la sesion de quien lo pidio.
        """
        if not obj.pk:
            return '—'

        if not obj.email:
            return _('No email on file: they cannot use the portal.')

        if obj.code_blocked_until and obj.code_blocked_until > timezone.now():
            return _('Blocked until %(when)s.') % {
                'when': timezone.localtime(obj.code_blocked_until).strftime(
                    '%d/%m/%Y %H:%M'
                )
            }

        if not obj.code_sends:
            return _('No code requested.')

        return _('%(sends)s sent in the current cycle.') % {
            'sends': obj.code_sends
        }

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

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .access import can_use_case_manager
from .models import CaseFinanceModel, CaseModel, ClientModel


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
    junto a la modalidad del contrato.
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
        (_('Payment modality'), {
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


@admin.register(CaseModel)
class CaseAdmin(CaseManagerAdminMixin, admin.ModelAdmin):
    inlines = [CaseFinanceInline]
    list_display = (
        'client', 'service', 'stage', 'is_active',
        'paz_y_salvo_authorized', 'updated',
    )
    list_filter = ('service', 'procedure', 'area', 'stage', 'is_active')
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


@admin.register(ClientModel)
class ClientAdmin(CaseManagerAdminMixin, admin.ModelAdmin):
    list_display = (
        'identification', 'full_name', 'email', 'is_active', 'code_state',
    )
    list_filter = ('is_active',)
    search_fields = ('identification', 'full_name', 'email')
    readonly_fields = ('code_state', 'created', 'updated')
    fields = (
        'identification', 'full_name', 'email', 'phone', 'is_active',
        'code_state', 'created', 'updated',
    )

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

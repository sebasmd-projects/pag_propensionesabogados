"""
Las rutas del modulo, en dos grupos que no se mezclan.

`consultar/proceso/` es el portal publico: sin sesion, con la clave del
cliente, y el dinero no sale de ahi.

`gestor/` es de puertas adentro: hace falta sesion y el grupo `gestor`, y el
dinero es justo lo que se viene a ver. La puerta la pone `GestorRequiredMixin`
en cada vista, no un `include` con un decorador: si manana alguien anade una
ruta aqui, tiene que elegir su mixin, y no heredar por descuido un permiso que
no penso.
"""

from django.urls import path
from django.utils.translation import gettext_lazy as _

from .gestor import (CaseCreateView, CaseListView, CaseNoteCreateView,
                     CaseToggleSettlementView, CaseUpdateView, CaseReportView,
                     ClientCreateView, ClientDetailView, ClientListView,
                     ClientReportView, ClientUpdateView, CrmReportView,
                     GestorDashboardView)
from .views import PazYSalvoView, PublicCaseQueryView

app_name = 'case_manager'

#: El portal publico.
public_urls = [
    path(
        'consultar/proceso/',
        PublicCaseQueryView.as_view(),
        name='public_query'
    ),
    path(
        'consultar/proceso/<uuid:pk>/paz-y-salvo/',
        PazYSalvoView.as_view(),
        name='paz_y_salvo'
    ),
]

#: El gestor interno. `gestor_title` y `gestor_section` los pinta
#: `gestor/base.html`: el titulo de la pantalla y la pestana que va marcada.
gestor_urls = [
    path(
        'gestor/asuntos/<uuid:pk>/ficha/descargar/',
        CaseReportView.as_view(),
        name='gestor_case_report',
    ),
    path(
        'gestor/',
        GestorDashboardView.as_view(
            extra_context={
                'gestor_title': _('Case manager'),
                'gestor_subtitle': _('Cases, clients and their money.'),
                'gestor_section': 'dashboard',
            }
        ),
        name='gestor_dashboard'
    ),

    path(
        'gestor/clientes/',
        ClientListView.as_view(
            extra_context={
                'gestor_title': _('Clients'),
                'gestor_section': 'clients',
            }
        ),
        name='gestor_client_list'
    ),
    path(
        'gestor/clientes/nuevo/',
        ClientCreateView.as_view(
            extra_context={
                'gestor_title': _('New client'),
                'gestor_section': 'clients',
            }
        ),
        name='gestor_client_create'
    ),
    path(
        'gestor/clientes/<uuid:pk>/ficha/',
        ClientDetailView.as_view(),
        name='gestor_client_detail'
    ),
    path(
        'gestor/clientes/<uuid:pk>/ficha/descargar/',
        ClientReportView.as_view(),
        name='gestor_client_report'
    ),
    path(
        'gestor/clientes/<uuid:pk>/',
        ClientUpdateView.as_view(
            extra_context={
                'gestor_title': _('Edit client'),
                'gestor_section': 'clients',
            }
        ),
        name='gestor_client_update'
    ),

    path(
        'gestor/asuntos/',
        CaseListView.as_view(
            extra_context={
                'gestor_title': _('Cases'),
                'gestor_section': 'cases',
            }
        ),
        name='gestor_case_list'
    ),
    path(
        'gestor/asuntos/nuevo/',
        CaseCreateView.as_view(
            extra_context={
                'gestor_title': _('New case'),
                'gestor_section': 'cases',
            }
        ),
        name='gestor_case_create'
    ),
    path(
        'gestor/asuntos/<uuid:pk>/',
        CaseUpdateView.as_view(
            extra_context={
                'gestor_title': _('Edit case'),
                'gestor_section': 'cases',
            }
        ),
        name='gestor_case_update'
    ),
    path(
        'gestor/asuntos/<uuid:pk>/notas/',
        CaseNoteCreateView.as_view(),
        name='gestor_case_note_create'
    ),
    path(
        'gestor/reporte/descargar/',
        CrmReportView.as_view(),
        name='gestor_crm_report'
    ),
    path(
        'gestor/asuntos/<uuid:pk>/paz-y-salvo/',
        CaseToggleSettlementView.as_view(),
        name='gestor_case_toggle_settlement'
    ),
]

urlpatterns = public_urls + gestor_urls

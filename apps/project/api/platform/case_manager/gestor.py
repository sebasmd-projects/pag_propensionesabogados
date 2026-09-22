"""
El gestor de procesos y clientes, como pantallas del sitio.

Por que no solo el admin
------------------------
El admin de Django resuelve la sesion, los permisos y la auditoria, y por eso
fue lo primero que se puso. Pero es una herramienta de desarrollo: habla en
sus terminos --«change list», «add another»--, no se parece al sitio, y no hay
manera de darle al despacho una pantalla pensada para su trabajo, como el
panel economico. Sigue ahi para el superusuario; el trabajo del dia a dia pasa
por aqui.

Por que va en un modulo aparte de `views.py`
--------------------------------------------
`views.py` es el portal publico: lo ve cualquiera con una cedula y una clave,
y su regla es que el dinero **no sale de ahi**. Esto es lo contrario: hace
falta sesion y grupo, y el dinero es justo lo que se viene a ver. Tenerlos en
ficheros distintos hace que la confusion tenga que ser deliberada.

La puerta
---------
Todas heredan `GestorRequiredMixin` (`access.py`), que es la misma pregunta
que contesta el admin: sesion iniciada, cuenta activa, y grupo `gestor` o
superusuario. A quien ha entrado pero no tiene el grupo se le responde 404, no
403: un 403 confirma que en esa direccion hay algo.
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from .access import GestorRequiredMixin
from .forms import CaseFinanceFormSet, CaseForm, ClientForm
from .models import CaseFinanceModel, CaseModel, ClientModel

#: Filas por pagina. La paginacion con filtros y ordenamiento propios esta
#: fuera del alcance contratado; esto es solo no servir mil filas de una vez.
PER_PAGE = 25


class GestorDashboardView(GestorRequiredMixin, TemplateView):
    """
    El panel economico y el gerencial.

    Es lo que en la pantalla anterior calculaba `actualizarPanelGerencial()`
    en el navegador, recorriendo `localStorage`. Ahora lo calcula la base:
    `CaseFinanceQuerySet.totals()` en **una** consulta, y las dos listas en
    una cada una.

    Las cifras y su significado estan explicados en `models.py`. La que mas
    se malentiende: `Cuota litis` al 0 % no es una expectativa, es un valor
    fijo cerrado, y cuenta como deuda.
    """

    template_name = 'case_manager/gestor/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['totals'] = CaseFinanceModel.objects.totals()
        context['debtors'] = (
            CaseFinanceModel.objects.debtors()
            .select_related('case', 'case__client')
            .order_by('-agreed_fee')[:10]
        )
        context['expectations'] = (
            CaseFinanceModel.objects.expectations()
            .select_related('case', 'case__client')
            .order_by('-contingency_value')[:10]
        )
        context['counters'] = ClientModel.objects.aggregate(
            clients=Count('pk'),
            active_clients=Count('pk', filter=Q(is_active=True)),
        )
        context['cases'] = CaseModel.objects.aggregate(
            total=Count('pk'),
            active=Count('pk', filter=Q(is_active=True)),
        )
        return context


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

class ClientListView(GestorRequiredMixin, ListView):
    """
    Los clientes del despacho, con busqueda por nombre o cedula.

    La busqueda es un `icontains` sobre dos columnas y nada mas. Filtros,
    ordenamiento por columna y busqueda global estan listados como trabajo
    aparte en la cotizacion.
    """

    model = ClientModel
    template_name = 'case_manager/gestor/client_list.html'
    context_object_name = 'clients'
    paginate_by = PER_PAGE

    def get_queryset(self):
        queryset = ClientModel.objects.annotate(case_count=Count('cases'))

        buscado = self.request.GET.get('q', '').strip()
        if buscado:
            queryset = queryset.filter(
                Q(full_name__icontains=buscado)
                | Q(identification__icontains=buscado)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class ClientCreateView(GestorRequiredMixin, CreateView):
    model = ClientModel
    form_class = ClientForm
    template_name = 'case_manager/gestor/client_form.html'
    success_url = reverse_lazy('case_manager:gestor_client_list')

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(
            self.request,
            _('Client %(name)s created. Their access key is %(key)s.') % {
                'name': self.object.full_name,
                'key': self.object.access_key,
            },
        )
        return respuesta


class ClientUpdateView(GestorRequiredMixin, UpdateView):
    model = ClientModel
    form_class = ClientForm
    template_name = 'case_manager/gestor/client_form.html'
    success_url = reverse_lazy('case_manager:gestor_client_list')

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, _('Client updated.'))
        return respuesta


# ---------------------------------------------------------------------------
# Asuntos
# ---------------------------------------------------------------------------

class CaseListView(GestorRequiredMixin, ListView):
    model = CaseModel
    template_name = 'case_manager/gestor/case_list.html'
    context_object_name = 'cases'
    paginate_by = PER_PAGE

    def get_queryset(self):
        queryset = CaseModel.objects.select_related('client', 'finance')

        buscado = self.request.GET.get('q', '').strip()
        if buscado:
            queryset = queryset.filter(
                Q(client__full_name__icontains=buscado)
                | Q(client__identification__icontains=buscado)
                | Q(case_number__icontains=buscado)
                | Q(administrative_case_number__icontains=buscado)
                | Q(police_case_number__icontains=buscado)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class CaseFormMixin:
    """
    El asunto y su dinero se guardan juntos o no se guarda ninguno.

    Son dos formularios --uno del asunto, otro del formset del dinero-- y un
    solo boton. Si se guardara el asunto y fallara el dinero, quedaria un
    expediente sin modalidad de contrato que no suma en ningun panel y que
    nadie sabria que esta a medias. La transaccion lo impide.

    (`ATOMIC_REQUESTS` ya envuelve la peticion entera, pero esto no depende de
    ese ajuste: si algun dia se quita, esto sigue siendo correcto.)
    """

    model = CaseModel
    form_class = CaseForm
    template_name = 'case_manager/gestor/case_form.html'
    success_url = reverse_lazy('case_manager:gestor_case_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if 'finance_formset' not in context:
            instancia = self.object if self.object and self.object.pk else None
            context['finance_formset'] = (
                CaseFinanceFormSet(self.request.POST, instance=instancia)
                if self.request.method == 'POST'
                else CaseFinanceFormSet(instance=instancia)
            )
        return context

    def form_valid(self, form):
        formset = CaseFinanceFormSet(
            self.request.POST, instance=form.instance
        )

        if not formset.is_valid():
            # `form_invalid` vuelve a pintar la pagina; el formset con sus
            # errores tiene que ir en el contexto o se pierden.
            return self.render_to_response(
                self.get_context_data(form=form, finance_formset=formset)
            )

        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

        messages.success(self.request, _('Case saved.'))
        return super(CaseFormMixin, self).form_valid(form)


class CaseCreateView(CaseFormMixin, GestorRequiredMixin, CreateView):
    pass


class CaseUpdateView(CaseFormMixin, GestorRequiredMixin, UpdateView):
    def get_queryset(self):
        return CaseModel.objects.select_related('client', 'finance')


class CaseToggleSettlementView(GestorRequiredMixin, UpdateView):
    """
    Autorizar o retirar el paz y salvo de un asunto, desde el listado.

    Es un `POST` y no un enlace a proposito: cambia un dato, y un `GET` que
    cambia datos lo dispara cualquier cosa que siga enlaces --un prefetch del
    navegador, un antivirus, un rastreador--.
    """

    model = CaseModel
    fields = ()
    http_method_names = ['post']
    success_url = reverse_lazy('case_manager:gestor_case_list')

    def form_valid(self, form):
        self.object.paz_y_salvo_authorized = (
            not self.object.paz_y_salvo_authorized
        )
        self.object.save(update_fields=['paz_y_salvo_authorized', 'updated'])

        plantilla = (
            _('Settlement letter enabled for %(name)s.')
            if self.object.paz_y_salvo_authorized
            else _('Settlement letter disabled for %(name)s.')
        )
        messages.success(
            self.request, plantilla % {'name': self.object.client.full_name}
        )
        return super().form_valid(form)

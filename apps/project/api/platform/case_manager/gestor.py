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

import uuid

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, TemplateView, View
from django.views.generic.edit import CreateView, UpdateView

from .access import GestorRequiredMixin
from .choices import NoteKind
from .emails import send_case_note
from .forms import CaseFinanceFormSet, CaseForm, CaseNoteForm, ClientForm
from .models import (CaseFinanceModel, CaseModel, CaseNoteModel, ClientModel)
from .reports import client_report, crm_report

#: Filas por pagina. La paginacion con filtros y ordenamiento propios esta
#: fuera del alcance contratado; esto es solo no servir mil filas de una vez.
PER_PAGE = 25


def _client_or_none(pedido):
    """
    El cliente de un `?cliente=<uuid>` de la URL, o `None`.

    Lo que llega en la URL lo escribe quien quiera, asi que hay dos maneras de
    que no sirva: que no exista ese cliente, o que el valor ni siquiera sea un
    UUID. La segunda **no** la absorbe `filter(pk=...)`: lanza
    `ValidationError` antes de tocar la base, y eso sale como un 500 por un
    enlace mal copiado.

    Las dos se tratan igual, ignorando el filtro: ensenar la lista entera es
    raro pero inofensivo, y una pagina de error por un enlace viejo no lo es.
    """
    if not pedido:
        return None

    try:
        uuid.UUID(str(pedido))
    except (ValueError, AttributeError, TypeError):
        return None

    return ClientModel.objects.filter(pk=pedido).first()


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
        context['areas'] = CaseFinanceModel.objects.by_area()
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
        # `order_by` explicito y no el del modelo: `annotate` agrupa, y una
        # consulta agrupada deja de considerarse ordenada --`queryset.ordered`
        # da falso-- aunque el `Meta` diga lo contrario. Sin esto, la base
        # devuelve las filas en el orden que le apetezca y un mismo cliente
        # puede salir en dos paginas y en ninguna. La cedula, que es unica,
        # desempata a los que se llaman igual.
        queryset = ClientModel.objects.annotate(
            case_count=Count('cases')
        ).order_by('full_name', 'identification')

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


class ClientDetailView(GestorRequiredMixin, DetailView):
    """
    La ficha de un cliente: quien es, que le debe al despacho y por que.

    Es la «ficha financiera individual» del panel aprobado, con una diferencia
    que viene del modelo y no de un capricho: alli un cliente **era** un
    asunto --una fila de `localStorage` por cedula-- y aqui un cliente puede
    tener varios. Asi que la ficha suma sus asuntos y ademas los desglosa;
    ensenar solo el ultimo, que es lo que haria una traduccion literal de
    aquella pantalla, es el mismo fallo que ya se corrigio en el portal.

    Las cifras de cabecera salen de `totals()` sobre **sus** asuntos: la misma
    consulta y las mismas reglas que el panel general, para que la ficha y el
    panel no puedan acabar diciendo cosas distintas del mismo cliente.
    """

    model = ClientModel
    template_name = 'case_manager/gestor/client_detail.html'
    context_object_name = 'client'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.object

        context['totals'] = CaseFinanceModel.objects.filter(
            case__client=cliente
        ).totals()

        context['cases'] = (
            CaseModel.objects.filter(client=cliente)
            .select_related('finance')
            .prefetch_related('notes')
            .order_by('-is_active', '-updated')
        )
        context['gestor_title'] = cliente.full_name
        context['gestor_subtitle'] = _('Client file and financial summary.')
        context['gestor_section'] = 'clients'
        return context


class ClientReportView(GestorRequiredMixin, DetailView):
    """
    La ficha de un cliente, descargada como `.docx`.

    Es una vista y no un boton de JavaScript porque el documento lo arma el
    servidor: la pantalla anterior lo construia en el navegador concatenando
    HTML con lo que tuviera `localStorage` delante, asi que el informe lo
    emitia quien lo leia y decia lo que hubiera en esa maquina.
    """

    model = ClientModel

    def render_to_response(self, context, **kwargs):
        return client_report(self.object)


class CrmReportView(GestorRequiredMixin, View):
    """El consolidado del portafolio, descargado como `.docx`."""

    def get(self, request, *args, **kwargs):
        return crm_report()


class CaseReportView(GestorRequiredMixin, DetailView):
    """Descarga el estado guardado de un único proceso del cliente."""

    model = CaseModel

    def render_to_response(self, context, **kwargs):
        return client_report(self.object.client, case=self.object)


class ClientCreateView(GestorRequiredMixin, CreateView):
    model = ClientModel
    form_class = ClientForm
    template_name = 'case_manager/gestor/client_form.html'
    success_url = reverse_lazy('case_manager:gestor_client_list')

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        if self.object.email:
            messages.success(
                self.request,
                _('Client %(name)s created. They will enter the portal with '
                  'their identification number and a code sent to '
                  '%(email)s.') % {
                    'name': self.object.full_name,
                    'email': self.object.email,
                },
            )
        else:
            # Sin correo no hay a donde mandar el codigo, y el cliente se
            # encontrara el portal cerrado sin saber por que. Mejor decirlo
            # ahora, cuando quien puede arreglarlo esta delante.
            messages.warning(
                self.request,
                _('Client %(name)s created, but without an email address they '
                  'cannot use the portal: the access code has nowhere to go.')
                % {'name': self.object.full_name},
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
    """
    Los asuntos del despacho, todos o los de un cliente.

    `?cliente=<uuid>` acota la lista a uno solo. Es lo que usa el boton del
    listado de clientes, y va por clave primaria y no por la busqueda de
    texto: buscar por la cedula traeria tambien a quien la tenga dentro de un
    numero de radicado, y «los asuntos de Fulano» tiene que ser exactamente
    eso.
    """

    model = CaseModel
    template_name = 'case_manager/gestor/case_list.html'
    context_object_name = 'cases'
    paginate_by = PER_PAGE

    def get_queryset(self):
        queryset = CaseModel.objects.select_related('client', 'finance')

        # Un identificador que no existe --o que ni siquiera es un UUID-- se
        # ignora y se ensena la lista entera, en vez de reventar con un 500
        # por un enlace viejo o mal copiado. `filter(pk=...)` **no** devuelve
        # vacio con un UUID mal formado: lanza `ValidationError`, asi que hay
        # que comprobarlo antes de preguntarle a la base.
        self.cliente = _client_or_none(self.request.GET.get('cliente'))
        if self.cliente is not None:
            queryset = queryset.filter(client=self.cliente)

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
        context['cliente'] = self.cliente
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

        if self.object and self.object.pk:
            context['notes'] = self.object.notes.select_related('created_by')
            context.setdefault('note_form', CaseNoteForm())

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

        # La etapa **de antes**, leida de la base antes de guardar. Hay que
        # cogerla aqui: despues de `form.save()` ya no existe en ningun sitio.
        etapa_anterior = (
            CaseModel.objects.filter(pk=form.instance.pk)
            .values_list('stage', flat=True)
            .first()
            if form.instance.pk
            else None
        )

        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

        messages.success(self.request, _('Case saved.'))
        self._notify_stage_change(form, etapa_anterior)
        return super(CaseFormMixin, self).form_valid(form)

    def _notify_stage_change(self, form, etapa_anterior) -> None:
        """
        Avisa al cliente de que su asunto avanzo, si procede.

        Tres condiciones, y las tres tienen que darse:

        1. que se marcara la casilla --el despacho decide cuando avisar, no
           el sistema: hay correcciones de etapa que no son novedades--;
        2. que la etapa **haya cambiado de verdad**. Guardar sin tocarla no
           es un avance, y un correo diciendo que el asunto avanzo cuando no
           ha avanzado gasta la confianza del siguiente;
        3. que sea un alta o un cambio, no un asunto recien creado sin etapa
           previa con la que comparar.

        La nota queda escrita aunque el correo no salga: es lo que pasa, y el
        expediente tiene que contarlo.
        """
        if not form.cleaned_data.get('notify_stage_change'):
            return

        if etapa_anterior is None or etapa_anterior == self.object.stage:
            return

        nota = CaseNoteModel.objects.create(
            case=self.object,
            kind=NoteKind.STAGE,
            title=_('Your procedure has moved forward'),
            body=_(
                'Your case is now at the stage «%(stage)s». We will keep you '
                'posted on any news.'
            ) % {'stage': self.object.get_stage_display()},
            visible_to_client=True,
            created_by=self.request.user,
        )

        if send_case_note(nota, request=self.request):
            messages.info(
                self.request,
                _('The client was emailed about the new stage.'),
            )
        else:
            messages.warning(
                self.request,
                _(
                    'The note was saved, but no email was sent: check that '
                    'the client has an email address on file.'
                ),
            )


class CaseCreateView(CaseFormMixin, GestorRequiredMixin, CreateView):
    """
    Alta de un asunto, con el cliente ya puesto si se vino desde su ficha.

    `?cliente=<uuid>` lo deja elegido en el desplegable. Es comodidad, no una
    restriccion: el campo sigue siendo editable, porque el desplegable es la
    unica manera de corregirse si se pulso el boton equivocado.
    """

    def get_initial(self):
        initial = super().get_initial()

        cliente = _client_or_none(self.request.GET.get('cliente'))
        if cliente is not None:
            initial['client'] = str(cliente.pk)
        return initial


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


class CaseNoteCreateView(GestorRequiredMixin, CreateView):
    """
    Anade una novedad a un asunto, y la manda al cliente si se marco.

    Es lo que el portal no tenia y por eso el cliente llamaba: la pantalla
    ensenaba la etapa y nada mas, asi que un asunto parado porque un juzgado
    no responde y otro parado porque falta su cedula se veian igual.

    Cuelga de la ficha del asunto --no tiene pagina propia-- porque una nota
    sin su expediente delante no se escribe bien.
    """

    model = CaseNoteModel
    form_class = CaseNoteForm
    http_method_names = ['post']

    def dispatch(self, request, *args, **kwargs):
        self.case = get_object_or_404(CaseModel, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('case_manager:gestor_case_update', args=[self.case.pk])

    def form_valid(self, form):
        form.instance.case = self.case
        form.instance.created_by = self.request.user
        self.object = form.save()

        messages.success(self.request, _('Note added.'))

        if form.cleaned_data.get('notify_client'):
            if send_case_note(self.object, request=self.request):
                messages.info(
                    self.request,
                    _('Emailed to %(email)s.') % {
                        'email': self.case.client.email
                    },
                )
            elif not self.object.visible_to_client:
                messages.info(
                    self.request,
                    _('Internal note: nothing was emailed to the client.'),
                )
            else:
                messages.warning(
                    self.request,
                    _(
                        'The note was saved, but no email was sent: check '
                        'that the client has an email address on file.'
                    ),
                )

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        """
        La nota no vale: se vuelve a la ficha con el formulario y sus errores,
        que es donde se estaba escribiendo.
        """
        from .forms import CaseFinanceFormSet as _Formset

        return render(
            self.request,
            'case_manager/gestor/case_form.html',
            {
                'form': CaseForm(instance=self.case),
                'finance_formset': _Formset(instance=self.case),
                'object': self.case,
                'notes': self.case.notes.select_related('created_by'),
                'note_form': form,
                'gestor_title': _('Edit case'),
                'gestor_section': 'cases',
            },
        )

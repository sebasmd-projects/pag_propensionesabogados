"""
El portal publico de consulta de procesos.

Lo que cambia respecto de lo que habia
--------------------------------------
Antes, `consultar/proceso/` servia una pagina que traia dentro **el expediente
de todos los clientes** (`localStorage.propDemo`) y decidia en el navegador si
ensenarlo. Quien abria el inspector tenia el despacho entero: nombres,
cedulas, areas, radicados.

Ahora la pagina llega vacia, el visitante manda identificacion y clave, y el
servidor responde **con un solo expediente**: el suyo. Lo que no se manda no se
puede mirar.

Por que una vista y no un endpoint de DRF
-----------------------------------------
El formulario es un `POST` de toda la vida desde una pagina renderizada por
Django, asi que la proteccion de CSRF viene puesta y la respuesta puede ser la
propia pagina. Meter DRF aqui obligaria a decidir como se autentica una cosa
que no tiene sesion, y el resultado seria el mismo con una pieza mas.
"""

import logging

from django.core.exceptions import ValidationError
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from . import attempts, portal_otp
from .forms import (NO_EMAIL_ON_FILE, INVALID_CODE, PublicAccessCodeForm,
                    PublicCaseQueryForm, UNKNOWN_IDENTIFICATION)
from .models import CaseModel, ClientModel

#: Donde se apunta a quien acaba de identificarse con su clave.
#:
#: No es una sesion de usuario --el cliente no tiene cuenta-- sino la memoria
#: de que en **esta** sesion alguien acerto la clave de ese cliente. Es lo que
#: permite que el paz y salvo sea una direccion propia sin quedar abierta a
#: cualquiera que la teclee.
SESSION_CLIENT_KEY = 'case_manager_client_id'

logger = logging.getLogger(__name__)

#: Lo que se responde a una IP bloqueada. No dice cuanto falta: eso le diria a
#: quien prueba cuando merece la pena volver.
BLOCKED_MESSAGE = _(
    'Too many failed attempts from this connection. Try again later.'
)

#: Cuando el correo no llega a salir. Se le dice, en vez de dejarle mirando un
#: campo vacio esperando un codigo que no viene.
CODE_NOT_SENT = _(
    'We could not send the access code right now. Please try again in a few '
    'minutes or contact us.'
)

#: Lo que se pone en lugar del correo tapado cuando el codigo fue al despacho.
#: La plantilla decide con `masked_email` que esta en el segundo paso, asi que
#: tiene que traer algo; lo que se lee en pantalla lo pone `sent_to_office`.
OFFICE_PLACEHOLDER = '-'



class PublicCaseQueryView(TemplateView):
    """
    El portal, en dos pasos: la cedula, y el codigo que llega al correo.

    Por que dos pasos
    -----------------
    Antes era uno: cedula y una «clave de acceso» que era la inicial del
    nombre mas los cuatro ultimos digitos de la propia cedula. Con la cedula
    delante, esa clave se calcula. O sea que el unico dato que hacia falta
    para abrir un expediente ajeno era un dato que circula.

    Ahora el segundo paso es un codigo de seis cifras que sale al correo que
    consta en el expediente. Quien lo recibe demuestra que controla ese buzon,
    y ese buzon es el que el cliente le dio al despacho. Eso si acredita
    titularidad; lo otro acreditaba saber una cedula.

    Las tres pantallas
    ------------------
    Son la misma direccion y el mismo formulario, en tres estados que se
    deciden por lo que hay en la sesion:

    1. **la cedula**, cuando no hay nada pendiente;
    2. **el codigo**, con el correo tapado y el boton de reenviar, mientras
       haya un codigo vivo;
    3. **los asuntos**, cuando el codigo se acerto.

    Una direccion y no tres porque el cliente no esta navegando: esta haciendo
    una gestion, y cada redireccion es un sitio mas donde perderse.
    """

    template_name = 'case_manager/consultar_proceso.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('form', PublicCaseQueryForm())
        context.setdefault('stages', CaseModel._meta.get_field('stage').choices)
        return context

    # -- lo que responde cada paso ----------------------------------------
    def _pantalla_del_codigo(self, client, **extra):
        """
        La pantalla del codigo: a donde fue, y cuando se puede repetir.

        `resend_at` sale en hora y no en segundos porque el cliente puede
        dejar esta pantalla abierta un rato, y unos segundos calculados al
        pintarla mentirian en cuanto pasen.
        """
        to_office = portal_otp.sent_to_office(self.request)

        return self.render_to_response(self.get_context_data(
            code_form=PublicAccessCodeForm(),
            # Con `to_office` no hay correo del cliente que tapar: lo que la
            # pantalla tiene que decir es que el codigo lo tiene el despacho y
            # hay que llamar. El campo sigue ahi porque la plantilla decide
            # con el que esta en el segundo paso.
            masked_email=client.masked_email or OFFICE_PLACEHOLDER,
            sent_to_office=to_office,
            office_notice=NO_EMAIL_ON_FILE,
            resend_at=portal_otp.next_send_allowed_at(client),
            **extra,
        ))

    def _cliente_pendiente(self):
        """
        El cliente cuyo codigo espera esta sesion, o `None`.

        Se relee de la base en vez de guardarlo entero en la sesion: entre que
        se pidio el codigo y se teclea, el despacho puede haberle dado de
        baja, y lo que vale es lo que diga la base ahora.
        """
        pk = portal_otp.pending_client_pk(self.request)

        if not pk:
            return None

        try:
            return ClientModel.objects.filter(pk=pk).first()
        except (ValidationError, ValueError):
            # Una sesion vieja con un identificador que ya no tiene forma de
            # UUID. `filter(pk=...)` levanta en vez de no encontrar nada.
            portal_otp.clear(self.request)
            return None

    def post(self, request, *args, **kwargs):
        ip = attempts.client_ip(request)

        if attempts.is_blocked(ip):
            return self.render_to_response(
                self.get_context_data(
                    form=PublicCaseQueryForm(),
                    error=BLOCKED_MESSAGE,
                ),
                status=429,
            )

        if 'resend' in request.POST:
            return self._reenviar(request, ip)

        if 'code' in request.POST:
            return self._comprobar_codigo(request, ip)

        return self._pedir_codigo(request, ip)

    # -- paso 1: la cedula ------------------------------------------------
    def _pedir_codigo(self, request, ip):
        form = PublicCaseQueryForm(request.POST)

        if not form.is_valid():
            attempts.register_failure(ip)
            return self.render_to_response(
                self.get_context_data(form=form, error=UNKNOWN_IDENTIFICATION),
                status=400,
            )

        client = form.get_client()

        if client is None:
            count = attempts.register_failure(ip)
            logger.info(
                'Consulta fallida en el portal de procesos desde %s (%s en la '
                'ventana actual).',
                ip, count,
            )
            return self.render_to_response(
                self.get_context_data(
                    form=form, error=UNKNOWN_IDENTIFICATION
                ),
                status=400,
            )

        if not portal_otp.can_send(client):
            # Ya pidio codigos de sobra. Se le ensena la pantalla del codigo
            # --el ultimo que recibio puede seguir sirviendo-- con la hora a
            # la que podra pedir otro.
            return self._pantalla_del_codigo(client)

        if not portal_otp.issue(request, client):
            return self.render_to_response(self.get_context_data(
                form=form, error=CODE_NOT_SENT, show_contact=True,
            ))

        return self._pantalla_del_codigo(client, code_sent=True)

    # -- reenviar ---------------------------------------------------------
    def _reenviar(self, request, ip):
        client = self._cliente_pendiente()

        if client is None:
            # La sesion caduco entre pedir el codigo y darle a reenviar. Se
            # vuelve al principio, que es lo unico que puede hacer.
            return self.render_to_response(
                self.get_context_data(form=PublicCaseQueryForm())
            )

        if not portal_otp.can_send(client):
            return self._pantalla_del_codigo(client)

        if not portal_otp.issue(request, client):
            return self.render_to_response(self.get_context_data(
                form=PublicCaseQueryForm(),
                error=CODE_NOT_SENT,
                show_contact=True,
            ))

        return self._pantalla_del_codigo(client, code_sent=True)

    # -- paso 2: el codigo ------------------------------------------------
    def _comprobar_codigo(self, request, ip):
        client = self._cliente_pendiente()

        if client is None:
            return self.render_to_response(
                self.get_context_data(form=PublicCaseQueryForm())
            )

        form = PublicAccessCodeForm(request.POST)

        if not form.is_valid() or not portal_otp.verify(
            request, form.cleaned_data.get('code', '')
        ):
            # Un codigo equivocado cuenta como intento fallido del portal:
            # si no, tantear seis cifras sale gratis mientras que equivocarse
            # de cedula no.
            attempts.register_failure(ip)
            return self._pantalla_del_codigo(
                client, code_error=INVALID_CODE
            )

        return self._entrar(request, ip, client)

    # -- dentro -----------------------------------------------------------
    def _entrar(self, request, ip, client):
        attempts.reset(ip)
        portal_otp.reset_ladder(client)

        # Rotar la sesion al identificarse: sin esto, un identificador de
        # sesion fijado de antemano por un tercero seguiria siendo valido
        # despues de que el cliente acierte su codigo.
        #
        # El codigo ya se consumio en `verify()`, asi que lo que se lleva por
        # delante el ciclo es solo el rastro.
        request.session.cycle_key()
        request.session[SESSION_CLIENT_KEY] = str(client.pk)

        # Sin vigencia: ni tarjeta ni mensaje de credenciales. El codigo era
        # bueno --acaba de demostrarlo-- asi que decirle que algo fallo solo
        # conseguiria que volviera a intentarlo. Se le dice que su proceso
        # esta inactivo y a donde llamar, que es lo unico que puede hacer.
        if not client.is_active:
            return self.render_to_response(
                self.get_context_data(form=PublicCaseQueryForm(), inactive=True)
            )

        # **Todos** sus asuntos, no el ultimo.
        #
        # Un cliente puede tener varios a la vez --una pension y una
        # conciliacion, por ejemplo--, y con `.first()` los demas no existian
        # para el: preguntaba por el que sabia que tenia y veia otro, sin
        # entender por que. El modelo siempre fue uno a muchos; la vista era
        # la que se quedaba con uno.
        cases = (
            CaseModel.objects.visible_to_client()
            .filter(client=client)
            # `finance` entra aqui porque la tarjeta ensena la modalidad del
            # contrato: sin esto es una consulta mas por cada asunto, y un
            # cliente con tres asuntos paga tres viajes a la base para pintar
            # tres palabras.
            .select_related('client', 'finance')
        )

        if not cases:
            # El cliente esta vigente pero no le queda ningun asunto que
            # ensenar --se cerraron todos--. Para el es la misma situacion que
            # la de arriba y tiene el mismo remedio: llamar al despacho.
            return self.render_to_response(
                self.get_context_data(form=PublicCaseQueryForm(), inactive=True)
            )

        return self.render_to_response(
            self.get_context_data(
                form=PublicCaseQueryForm(), client=client, cases=cases
            )
        )


class PazYSalvoView(TemplateView):
    """
    El paz y salvo de un caso, emitido por el servidor.

    Antes lo escribia el navegador en una ventana nueva, concatenando los
    datos que tuviera `localStorage` delante. O sea: lo expedia quien lo leia,
    con el nombre que quisiera.

    Ahora hacen falta las tres cosas a la vez, y las tres las comprueba esta
    vista:

    1. que el despacho lo haya autorizado en ese caso concreto;
    2. que el caso este vigente y el cliente tambien;
    3. que quien lo pide sea **ese** cliente, identificado con su clave en
       esta misma sesion.

    Falla con 404 en los tres casos, y a proposito: un 403 confirmaria que ese
    caso existe, que es justo lo que no tiene por que saber quien teclea
    identificadores a ver que sale.
    """

    template_name = 'case_manager/paz_y_salvo.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        session_client = self.request.session.get(SESSION_CLIENT_KEY)
        if not session_client:
            raise Http404

        case = (
            CaseModel.objects.visible_to_client()
            .filter(
                pk=kwargs['pk'],
                client_id=session_client,
                paz_y_salvo_authorized=True,
            )
            .select_related('client')
            .first()
        )

        if case is None:
            raise Http404

        context['case'] = case
        context['issued_at'] = timezone.localtime()
        return context

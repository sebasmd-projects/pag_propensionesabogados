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

from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from . import attempts
from .forms import INVALID_CREDENTIALS, PublicCaseQueryForm
from .models import CaseModel

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


class PublicCaseQueryView(TemplateView):
    """
    Pide identificacion y clave, y devuelve un expediente o nada.

    En `GET` la pagina sale vacia: sin `case` en el contexto, la plantilla no
    pinta la tarjeta del cliente.
    """

    template_name = 'case_manager/consultar_proceso.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('form', PublicCaseQueryForm())
        context.setdefault('stages', CaseModel._meta.get_field('stage').choices)
        return context

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

        form = PublicCaseQueryForm(request.POST)
        if not form.is_valid():
            attempts.register_failure(ip)
            return self.render_to_response(
                self.get_context_data(form=form, error=INVALID_CREDENTIALS),
                status=400,
            )

        client = form.get_client()
        if client is None:
            count = attempts.register_failure(ip)
            logger.info(
                'Consulta fallida en el portal de procesos desde %s (%s en la '
                'ventana actual).',
                ip,
                count,
            )
            return self.render_to_response(
                self.get_context_data(form=form, error=INVALID_CREDENTIALS),
                status=400,
            )

        attempts.reset(ip)

        # Rotar la sesion al identificarse: sin esto, un identificador de
        # sesion fijado de antemano por un tercero seguiria siendo valido
        # despues de que el cliente acierte su clave.
        request.session.cycle_key()
        request.session[SESSION_CLIENT_KEY] = str(client.pk)

        # Sin vigencia: ni tarjeta ni mensaje de credenciales. La clave era
        # buena --acaba de demostrarlo-- asi que decirle «credenciales
        # invalidas» solo conseguia que siguiera probando claves correctas
        # hasta gastar los intentos de su propia IP. Se le dice que su proceso
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
            # la de arriba y tiene el mismo remedio: llamar al despacho. Asi
            # que es la misma pantalla, y no un aviso distinto que le haria
            # pensar que se equivoco al escribir algo.
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

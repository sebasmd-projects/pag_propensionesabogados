"""
El asistente de acceso, con una segunda puerta: el codigo por correo.

Por que va **dentro** del asistente de `django-two-factor-auth`
---------------------------------------------------------------
Porque el asistente decide el solo si hace falta el paso del segundo factor,
mirando si la cuenta tiene dispositivo configurado. Lo unico que hace el paso
nuevo es dejar el usuario identificado en el primer paso, exactamente como el
formulario de contrasena; a partir de ahi el flujo es el de siempre y el TOTP
se sigue pidiendo.

Una vista aparte que llamara a `login()` habria sido mucho mas corta y habria
convertido el acceso al correo en una forma de saltarse el segundo factor de
otra persona. Eso no es una comodidad, es una puerta trasera.

Los pasos
---------

    auth    usuario y contrasena            <- siempre presente
    otp     usuario/correo **y** el codigo  <- solo en modo codigo
    token   el segundo factor, si lo hay
    backup  el codigo de respaldo

**El segundo factor es opcional.** Quien no lo ha configurado no ve `token`
ni `backup`: la biblioteca los descarta sola. Configurarlo esta en el perfil
(`two_factor:setup`) y no en el registro.

**El codigo es una sola pantalla, no dos.** Ensena el identificador y el
codigo a la vez, con un boton que manda el correo y otro que entra. Partirlo
en dos --escribe el correo, pulsa, ahora escribe el codigo-- obligaba a
descubrir a mitad de camino que habia un segundo tramo.

**El de contrasena no sale nunca de la lista.** Es lo que separa ofrecer el
codigo de capar los intentos: si al ofrecerlo se quitara `auth`, un envio de
contrasena posterior no llegaria a validarse, `django-axes` no contaria ese
fallo y su bloqueo no se alcanzaria jamas desde el navegador. La oferta
llegaria antes que el freno y de paso lo apagaria.

**Los tres caminos cuentan en el mismo sitio.** Contrasena, codigo y segundo
factor apuntan sus fallos con `login_attempts.note_failure()` y preguntan por
el bloqueo con `is_locked_out()`. Contando solo la contrasena, el camino mas
barato para quien ataca es justo el que no deja rastro.
"""

import logging
import time

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from two_factor.forms import AuthenticationTokenForm, BackupTokenForm
from two_factor.views import LoginView as TwoFactorLoginView

from apps.common.utils.login_attempts import is_locked_out, note_failure
from apps.common.utils.wizards import forget_resolved_steps

from . import otp_login
from .forms import LoginOTPForm

logger = logging.getLogger(__name__)

#: Donde se recuerda por que puerta se esta entrando. Fuera del almacen del
#: asistente a proposito: ese se vacia y se llevaria el modo con el.
MODE_KEY = 'login_mode'

#: Fallos de contrasena seguidos en este navegador.
FAILURES_KEY = 'login_password_failures'

#: Si ya se ofrecio el codigo en este intento. La oferta es una sola: volver a
#: ofrecerlo en cada fallo posterior devolveria a la pantalla del codigo a
#: quien acaba de pedir expresamente seguir con la contrasena.
OFFERED_KEY = 'login_otp_offered'

#: Con que texto se identifico quien esta entrando. Hace falta guardarlo
#: porque el segundo factor llega cuando ya no hay campo de usuario en
#: pantalla, y `django-axes` cuenta por lo **tecleado**: quien entra con su
#: correo y luego falla el TOTP alimentaria una cuenta atras distinta de la
#: del primer paso. Dos contadores para el mismo intruso son ninguno.
ATTEMPT_KEY = 'login_attempt_username'

MODE_PASSWORD = 'password'
MODE_OTP = 'otp'

#: El boton «enviar el codigo». Va por su nombre en el POST y no como un paso
#: del asistente porque no es un paso: no valida nada, manda un correo y
#: vuelve a pintar la misma pantalla.
SEND_ACTION = 'send_code'


class PropensionesLoginView(TwoFactorLoginView):
    """El asistente de siempre, mas la entrada por codigo."""

    OTP_STEP = 'otp'

    form_list = (
        (TwoFactorLoginView.AUTH_STEP, TwoFactorLoginView.form_list[0][1]),
        (OTP_STEP, LoginOTPForm),
        (TwoFactorLoginView.TOKEN_STEP, AuthenticationTokenForm),
        (TwoFactorLoginView.BACKUP_STEP, BackupTokenForm),
    )

    template_name = 'two_factor/core/login.html'

    def get_prefix(self, request, *args, **kwargs):
        """
        El prefijo del asistente se queda como `login_view`.

        `formtools` lo saca del nombre de la clase, asi que heredar de
        `LoginView` con otro nombre renombraria de paso el campo de control
        que manda la pagina --`login_view-current_step` pasaria a ser
        `propensiones_login_view-current_step`-- y la clave del almacen en la
        sesion. Lo primero es el contrato de la pantalla; lo segundo deja
        tirado a quien tuviera un acceso a medias en el momento del
        despliegue.
        """
        return 'login_view'

    # ------------------------------------------------------------------
    # Que pasos entran
    # ------------------------------------------------------------------
    def _mode(self):
        return self.request.session.get(MODE_KEY, MODE_PASSWORD)

    def _set_mode(self, mode):
        self.request.session[MODE_KEY] = mode
        self._forget_resolved_steps()

    def _forget_resolved_steps(self):
        """
        Tira la lista de pasos que `formtools` guarda en cache.

        La condicion del paso `otp` mira el modo, que vive en la sesion y
        cambia a mitad de peticion; la cache de `formtools` no puede saberlo
        (ver `apps/common/utils/wizards.py`). Sin esto, entrar en modo codigo
        deja `otp` como paso actual y luego lo busca en una lista resuelta
        **antes** del cambio: `KeyError: 'otp'`. Y al reves al salir.

        Se invalida aqui, en `_set_mode()`, y no en cada sitio que cambia de
        modo: es el unico punto por el que pasa el cambio, y una invalidacion
        que hay que acordarse de llamar es la que se olvida.
        """
        forget_resolved_steps(self)

    def has_otp_step(self):
        return self._mode() == MODE_OTP

    #: `AUTH_STEP` no aparece aqui a proposito: sin condicion, el asistente lo
    #: incluye siempre. Ver el encabezado del modulo.
    condition_dict = {
        OTP_STEP: has_otp_step,
        TwoFactorLoginView.TOKEN_STEP: TwoFactorLoginView.has_token_step,
        TwoFactorLoginView.BACKUP_STEP: TwoFactorLoginView.has_backup_step,
    }

    # ------------------------------------------------------------------
    # Entrar y salir del modo codigo
    # ------------------------------------------------------------------
    def _enter_otp_mode(self, identifier='', send=True):
        """
        Deja el asistente en la pantalla del codigo.

        `send` sale en `False` cuando solo se quiere abrir la pantalla --el
        boton «entrar con un codigo»--, porque ahi todavia no se sabe a quien
        mandarlo.
        """
        self._set_mode(MODE_OTP)
        self.storage.reset()

        identifier = (identifier or '').strip()

        if send and identifier:
            # El envio pasa por su cupo, que falla cerrado. Si no hay cupo, la
            # pantalla sale igual: el aviso no promete que el correo saliera, y
            # decir aqui que no salio delataria que la cuenta existe.
            otp_login.issue(self.request, identifier)
        elif identifier:
            otp_login.remember_identifier(self.request, identifier)

        self.storage.current_step = self.OTP_STEP

    def post(self, *args, **kwargs):
        request = self.request

        # «Entrar con un codigo»: abre la pantalla, todavia sin mandar nada.
        # Quien lo pulsa puede no haber escrito su usuario aun.
        if 'use_otp' in request.POST:
            otp_login.clear(request)
            self._enter_otp_mode(
                request.POST.get('auth-username', ''), send=False
            )
            return self.render(self.get_form())

        # «Enviar el codigo»: manda el correo y vuelve a la misma pantalla. No
        # pasa por la validacion del formulario porque el codigo todavia no
        # existe; exigirlo para poder pedirlo seria un circulo.
        if SEND_ACTION in request.POST:
            self._enter_otp_mode(request.POST.get('otp-identifier', ''))
            return self.render(self.get_form())

        if 'use_password' in request.POST:
            self._set_mode(MODE_PASSWORD)
            otp_login.clear(request)
            self.storage.reset()
            self.storage.current_step = self.AUTH_STEP
            return self.render(self.get_form())

        return super().post(*args, **kwargs)

    def step_requires_authentication(self, step):
        """
        Que pasos exigen que el usuario ya este identificado.

        El del codigo **no**: es el que identifica, igual que el de
        contrasena. La biblioteca da por hecho que solo el primer paso va
        antes de la identificacion, y con el reloj de caducidad eso se traduce
        en que, al mandar el codigo, el asistente lo toma por una sesion
        caducada --`authentication_time` todavia no existe, asi que la cuenta
        sale negativa--, reinicia el almacen y vuelve a pedir el correo sin
        haber llegado a mirar el codigo. Ni error en pantalla, ni intento
        contado: parece que el boton no hace nada.
        """
        if step == self.OTP_STEP:
            return False

        return super().step_requires_authentication(step)

    # ------------------------------------------------------------------
    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)

        if step == self.OTP_STEP:
            kwargs['request'] = self.request

        return kwargs

    def get_form_initial(self, step):
        initial = super().get_form_initial(step)

        if step == self.OTP_STEP:
            # El identificador que ya se tecleo vuelve escrito. Volver a
            # pedirlo tras pulsar «enviar» haria dudar de si el correo salio.
            initial = dict(initial or {})
            initial.setdefault(
                'identifier', otp_login.entered_identifier(self.request)
            )

        return initial

    def process_step(self, form):
        """
        Lo que pasa al superar cada paso.

        El paso del codigo hace lo mismo que el de contrasena: dejar el
        usuario identificado. Lo que venga despues --el segundo factor-- es
        identico para los dos.
        """
        step = self.steps.current

        if step in (self.AUTH_STEP, self.OTP_STEP):
            self.request.session[ATTEMPT_KEY] = self._attempted_username(form)

        if step == self.AUTH_STEP:
            # La contrasena acerto, asi que el rodeo del codigo termina aqui.
            # Si el modo siguiera puesto, su paso seguiria en la lista y el
            # asistente pediria un correo a quien acaba de identificarse.
            self._set_mode(MODE_PASSWORD)
            otp_login.clear(self.request)
            self.request.session.pop(FAILURES_KEY, None)

        if step == self.OTP_STEP:
            # Sin `storage.reset()`, al contrario que el paso de contrasena.
            #
            # Alli el reinicio existe para no dejar la contrasena escrita en
            # la sesion, y funciona porque `auth` es a la vez el primer paso y
            # el ultimo. Aqui no: reiniciar devuelve `current_step` al
            # principio, el asistente deja de ver que esta en el ultimo paso y
            # en vez de terminar vuelve a pedir el codigo, en bucle.
            #
            # Y no hace falta: el paso no guarda nada --devuelve `None`-- y el
            # codigo ya lo consumio `verify()`.
            self.storage.authenticated_user = form.user_cache

            # El mismo sello que pone el paso de contrasena. Es el que mira
            # `expired` para los pasos que vienen despues; sin el, el segundo
            # factor se toma por una sesion caducada nada mas llegar.
            self.storage.data['authentication_time'] = int(time.time())

            self.request.session.pop(FAILURES_KEY, None)
            return None

        return super().process_step(form)

    def get_done_form_list(self):
        """
        Que formularios se revalidan al terminar.

        Ni el de contrasena ni el del codigo: no se guarda lo que se teclea en
        ellos, asi que revalidarlos seria validar formularios vacios y el
        acceso fallaria siempre. La biblioteca hace lo mismo con el suyo.

        `super()` hace `pop(AUTH_STEP)` sin valor por defecto, y en modo
        codigo ese paso podria no estar: se parte de `get_form_list()` y se
        quitan los dos a la vez.
        """
        form_list = self.get_form_list()

        for step in (self.AUTH_STEP, self.OTP_STEP):
            form_list.pop(step, None)

        return form_list

    def done(self, form_list, **kwargs):
        # Que no quede nada del camino: ni el modo, ni el contador, ni el
        # codigo. Si no, el siguiente que entre por este navegador se
        # encontraria el asistente a medias.
        for key in (MODE_KEY, FAILURES_KEY, OFFERED_KEY, ATTEMPT_KEY):
            self.request.session.pop(key, None)

        otp_login.clear(self.request)

        # Quitar el modo tambien cambia que pasos hay, asi que la cache de
        # `formtools` tiene que enterarse igual que al ponerlo.
        self._forget_resolved_steps()

        if not self.get_user():
            return self._restart_without_user()

        return super().done(form_list, **kwargs)

    def _restart_without_user(self):
        """
        Vacia el asistente y devuelve a la primera pantalla, con aviso.

        `get_user()` puede devolver **`False`**, y eso no se puede pasar a
        `login()`. El almacen guarda al usuario como dos datos sueltos
        --`user_pk` y `user_backend`-- y su lector devuelve `False`, no
        `None`, cuando falta alguno o cuando el backend ya no puede cargar esa
        cuenta. Si ese `False` llega a `login()`, Django le busca un atributo
        `backend`, no lo encuentra, y con tres backends configurados acaba en
        «You have multiple authentication backends configured»: un 500 en la
        pantalla de acceso.

        Puede pasar porque la sesion se perdiera entre dos peticiones, porque
        quedara un asistente a medias de una version anterior, o porque la
        cuenta se desactivara entre identificarse y terminar. En los tres
        casos la respuesta correcta es la misma y no es reventar: no hay
        usuario, luego no hay acceso; se vacia lo que quedara y se vuelve a
        empezar, diciendolo. Se registra porque un reinicio silencioso es
        indistinguible de un boton que no hace nada.
        """
        logger.warning(
            'Acceso: se llego al final del asistente sin usuario en el '
            'almacen. paso=%s pasos=%s modo=%s',
            self.storage.current_step,
            list(self.get_form_list()),
            self._mode(),
        )

        self.storage.reset()
        self.storage.current_step = self.AUTH_STEP
        self._set_mode(MODE_PASSWORD)

        messages.error(self.request, _(
            'Your sign-in could not be completed because the session was '
            'lost. Please sign in again.'
        ))

        # Se responde con una redireccion y no repintando la pantalla: asi el
        # navegador queda en un GET y recargar no reenvia el formulario a un
        # asistente que ya no existe.
        return redirect(self.request.path)

    # ------------------------------------------------------------------
    # Los fallos, que ahora cuentan los tres
    # ------------------------------------------------------------------
    def _attempted_username(self, form):
        """Quien intentaba entrar, mire el paso que mire."""
        step = self.steps.current

        if step == self.AUTH_STEP:
            return (form.data.get('auth-username') or '').strip()

        if step == self.OTP_STEP:
            return (form.data.get('otp-identifier') or '').strip()

        # En el segundo factor y en el de respaldo ya no hay campo de usuario
        # en pantalla: se usa lo que se tecleo al identificarse.
        return self.request.session.get(ATTEMPT_KEY, '')

    def render(self, form=None, **kwargs):
        """
        Cuenta los fallos y, al tercero de contrasena, ofrece el codigo.

        Se cuenta aqui y no en `process_step` porque ese solo se llama con el
        formulario valido, y lo que hay que contar es justo lo contrario.

        El segundo factor y el de respaldo se apuntan igual. No pasan por
        `authenticate()`, asi que sus fallos no llegaban a `axes`: probar
        codigos TOTP salia gratis mientras que probar contrasenas no, y el
        freno estorbaba solo a quien no atacaba.
        """
        failed = (
            self.request.method == 'POST'
            and form is not None
            and form.is_bound
            and bool(form.errors)
        )
        step = self.steps.current

        if failed and step in (self.TOKEN_STEP, self.BACKUP_STEP):
            note_failure(
                self.request, self._attempted_username(form),
                reason=f'login {step}',
            )

        if failed and step == self.AUTH_STEP:
            failures = int(self.request.session.get(FAILURES_KEY, 0)) + 1
            self.request.session[FAILURES_KEY] = failures

            already_offered = bool(self.request.session.get(OFFERED_KEY))
            identifier = self._attempted_username(form)

            if (failures >= otp_login.FAILURES_BEFORE_OFFER
                    and not already_offered and identifier):
                self.request.session[OFFERED_KEY] = True
                self._enter_otp_mode(identifier)

                return super().render(self.get_form(), **kwargs)

        return super().render(form, **kwargs)

    # ------------------------------------------------------------------
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)

        step = self.steps.current

        context['login_mode'] = self._mode()
        context['otp_step_name'] = self.OTP_STEP
        context['otp_send_action'] = SEND_ACTION
        context['otp_minutes'] = otp_login.ttl_minutes()
        context['otp_contact_email'] = otp_login.contact_email()
        context['otp_code_sent'] = otp_login.has_live_code(self.request)
        context['password_failures'] = int(
            self.request.session.get(FAILURES_KEY, 0)
        )
        context['otp_failures_before_offer'] = otp_login.FAILURES_BEFORE_OFFER

        # El aviso de bloqueo se pinta antes de que el paso lo compruebe, para
        # que quien ya esta fuera no siga tecleando codigos que nadie va a
        # mirar.
        context['locked_out'] = (
            step in (self.OTP_STEP, self.TOKEN_STEP, self.BACKUP_STEP)
            and is_locked_out(self.request, self._attempted_username(form))
        )

        context['step_title'], context['step_lead'] = self._step_copy(step)

        return context

    def _step_copy(self, step):
        """Titulo y frase de cada pantalla, en un solo sitio."""
        if step == self.OTP_STEP:
            return (
                _('Sign in with a code'),
                _('We send a six-digit code to the email on your account.'),
            )

        if step == self.TOKEN_STEP:
            return (
                _('Two-step verification'),
                _('Enter the code from your authentication app.'),
            )

        if step == self.BACKUP_STEP:
            return (
                _('Backup token'),
                _('Enter one of the backup tokens you saved when you set up '
                  'two-step verification.'),
            )

        return (
            _('Sign in'),
            _('Enter your credentials to access your account.'),
        )

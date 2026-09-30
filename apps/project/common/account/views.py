import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
from django.views.generic.edit import FormView

from apps.common.utils.client_ip import get_client_ip
from apps.common.utils.login_attempts import is_locked_out, note_failure
from apps.common.utils.throttling import RateLimit
from apps.project.common.users.models import UserModel

from .emails import send_password_reset_email
from .forms import (
    ChangePasswordForm,
    ForgotPasswordStep1Form,
    ForgotPasswordStep2Form,
    UserRegisterForm,
)

logger = logging.getLogger(__name__)

# El acceso vive en `login_view.PropensionesLoginView`, que es el asistente de
# `django-two-factor-auth` con la entrada por codigo al correo. Aqui estaba
# antes un `FormView` que llamaba a `authenticate()` sin la peticion, asi que
# `django-axes` no podia contar nada ni aplicar ningun bloqueo.


class UserLogoutView(View):
    def get(self, request, *args, **kwargs):
        from django.contrib.auth import logout

        logout(request)
        return HttpResponseRedirect(
            reverse(
                'account:login'
            )
        )


class UserRegisterView(FormView):
    template_name = "account/register.html"
    form_class = UserRegisterForm

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('core:index')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        UserModel.objects.create_user(
            username=form.cleaned_data['username'],
            email=form.cleaned_data['email'],
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
            password=form.cleaned_data['password'],
        )
        return super(UserRegisterView, self).form_valid(form)

    def form_invalid(self, form):
        return super(UserRegisterView, self).form_invalid(form)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        else:
            return reverse('core:index')


class ForgotPasswordFormView(View):
    """
    "Olvide mi contrasena", en dos pasos sobre una sola URL.

    1. Se escribe el usuario o el correo y llega un enlace de un solo uso.
    2. El enlace lleva a fijar la clave nueva, con los validadores de Django.

    Es el unico punto de la plataforma donde **alguien sin sesion provoca el
    envio de un correo**, y eso obliga a cuidar cuatro cosas:

    1. **Un limite de envios.** Sin el, repetir el formulario con el correo de
       otra persona le llena la bandeja y de paso quema la cuota del proveedor
       de correo. Hay dos cupos: por destinatario y por IP. Sin el primero se
       llena un buzon; sin el segundo se recorre una lista de usuarios mandando
       tres a cada uno. Los dos **fallan cerrados** (ver `RateLimit`).
    2. **Que la respuesta no delate quien tiene cuenta.** Todas las ramas --la
       cuenta existe o no, hay cupo o no, el correo sale o falla-- terminan en
       la misma pantalla. Un fallo de SMTP no puede ser un 500 para quien
       existe y una pagina normal para quien no.
    3. **Que el enlace no salga del host de la peticion.** Se construye con
       `PUBLIC_BASE_URL`, no con la cabecera `Host`, que pone el cliente.
    4. **Que el enlace sea de un solo uso y caduque.** El generador de Django
       firma con el hash de la clave actual y la fecha del ultimo acceso: en
       cuanto se cambia la clave, el enlace deja de valer. Caduca a los
       `PASSWORD_RESET_TIMEOUT` segundos.

    Y una precaucion mas, que no estaba en GEA: al abrir el enlace, el
    identificador y el codigo pasan a la **sesion** y el navegador se
    redirige a la URL limpia. Asi el codigo no se queda en la barra de
    direcciones ni viaja en la cabecera `Referer` a cualquier recurso externo
    que cargue la pantalla. Es lo que hace el restablecimiento de Django.

    Aviso sobre los cupos: viven en cache, y sin `CACHES` configurado Django
    usa `LocMemCache`, que es por proceso. Con varios workers el limite es
    efectivamente por worker.
    """

    template_name = 'account/forgot_password.html'
    token_generator = default_token_generator

    #: Donde espera el paso 2 lo que trajo el enlace.
    SESSION_KEY = 'password_reset_link'

    # Ventana y cupos del limite de envios.
    RESET_RATE_TTL_SECONDS = 15 * 60
    RESET_MAX_SENDS_PER_TARGET = 3
    RESET_MAX_SENDS_PER_IP = 10

    # El de destinatario va por `scope`, sin la IP dentro: el cupo de un buzon
    # tiene que ser del buzon, o rotar de IP lo rellenaria.
    reset_by_target = RateLimit(
        'reset_target',
        limit=RESET_MAX_SENDS_PER_TARGET,
        window=RESET_RATE_TTL_SECONDS,
    )
    reset_by_ip = RateLimit(
        'reset_ip',
        limit=RESET_MAX_SENDS_PER_IP,
        window=RESET_RATE_TTL_SECONDS,
    )

    # ------------------------------------------------------------------
    def get(self, request, *args, **kwargs):
        uidb64 = request.GET.get('uidb64')
        token = request.GET.get('token')

        # Llega desde el correo: se guarda y se limpia la URL.
        if uidb64 and token:
            request.session[self.SESSION_KEY] = {
                'uidb64': uidb64, 'token': token,
            }
            return redirect('account:forgot_password')

        if request.session.get(self.SESSION_KEY):
            return self._handle_step2_get(request)

        return self._handle_step1_get(request)

    def post(self, request, *args, **kwargs):
        if request.session.get(self.SESSION_KEY):
            return self._handle_step2_post(request)

        return self._handle_step1_post(request)

    # ------------------------------------------------------------------
    # Paso 1: pedir el enlace
    # ------------------------------------------------------------------
    def _handle_step1_get(self, request):
        return render(request, self.template_name, {
            'form': ForgotPasswordStep1Form(),
            'step': 1,
            'title': _('Reset Your Password'),
        })

    def _sent_response(self, request):
        """
        La unica pantalla con la que termina el paso 1, pase lo que pase.

        Existir o no existir, tener cupo o haberlo agotado, y que el correo
        salga o falle, dan todos el mismo resultado visible. Es lo que impide
        usar el formulario para averiguar quien tiene cuenta.
        """
        return render(request, self.template_name, {
            'step': 'success',
            'title': _('Check Your Email'),
            'message': _(
                'If an account exists with the provided email/username, '
                'you will receive password reset instructions shortly.'
            ),
        })

    def _handle_step1_post(self, request):
        form = ForgotPasswordStep1Form(request.POST)

        if not form.is_valid():
            # Solo cae aqui si el campo viene vacio o es demasiado largo.
            return render(request, self.template_name, {
                'form': form,
                'step': 1,
                'title': _('Reset Your Password'),
            })

        identifier = form.cleaned_data['email_or_username']
        users = form.get_users()

        # El cupo por IP se consume siempre, exista la cuenta o no. El de
        # destinatario, por el **correo de la cuenta** cuando la hay: si fuera
        # por lo tecleado, pedir una vez por el usuario y otra por el correo
        # abriria dos cupos para el mismo buzon.
        ip_ok = self.reset_by_ip.consume(request)

        if not users:
            self.reset_by_target.consume(request, scope=identifier)
            return self._sent_response(request)

        for user in users:
            target_ok = self.reset_by_target.consume(
                request, scope=user.email.strip().lower()
            )

            if not (ip_ok and target_ok):
                logger.warning(
                    'Password reset rate limit hit from %s',
                    get_client_ip(request),
                )
                continue

            self._send_password_reset_email(user)

        return self._sent_response(request)

    def _send_password_reset_email(self, user):
        """
        Manda el correo de restablecimiento. No propaga fallos a proposito.

        Un fallo de SMTP no puede convertirse en un error 500, porque entonces
        la respuesta distinta delataria que ese usuario existe. Se registra y
        la pantalla sigue siendo la misma.
        """
        base = str(getattr(settings, 'PUBLIC_BASE_URL', '')).rstrip('/')

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = self.token_generator.make_token(user)
        path = reverse('account:forgot_password')
        reset_url = f'{base}{path}?uidb64={uid}&token={token}'

        try:
            send_password_reset_email(
                user=user,
                reset_url=reset_url,
                minutes=int(settings.PASSWORD_RESET_TIMEOUT) // 60,
            )
        except Exception:                                   # noqa: BLE001
            logger.exception('Password reset email could not be sent')

    # ------------------------------------------------------------------
    # Paso 2: fijar la clave nueva
    # ------------------------------------------------------------------
    def _user_from_link(self, request):
        """La cuenta a la que corresponde el enlace guardado, o `None`."""
        link = request.session.get(self.SESSION_KEY) or {}

        try:
            uid = force_str(urlsafe_base64_decode(link.get('uidb64', '')))
            user = get_user_model()._default_manager.get(pk=uid)
        except (
            TypeError, ValueError, OverflowError, ValidationError,
            get_user_model().DoesNotExist,
        ):
            # `ValidationError` porque la clave primaria es un UUID: un
            # identificador que no lo es no llega a ser una consulta.
            return None

        if not user.is_active:
            return None

        if not self.token_generator.check_token(user, link.get('token', '')):
            return None

        return user

    def _invalid_link(self, request):
        request.session.pop(self.SESSION_KEY, None)
        messages.error(request, _(
            'The password reset link is invalid or has expired. '
            'Please request a new password reset.'
        ))

        # Se pinta el paso 1 en la misma respuesta, sin redirigir: redirigir a
        # la misma URL seria una vuelta mas para acabar donde ya se esta.
        return self._handle_step1_get(request)

    def _handle_step2_get(self, request):
        user = self._user_from_link(request)

        if user is None:
            return self._invalid_link(request)

        return render(request, self.template_name, {
            'form': ForgotPasswordStep2Form(user),
            'step': 2,
            'title': _('Set New Password'),
        })

    def _handle_step2_post(self, request):
        user = self._user_from_link(request)

        if user is None:
            return self._invalid_link(request)

        form = ForgotPasswordStep2Form(user, request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form,
                'step': 2,
                'title': _('Set New Password'),
            })

        form.save()
        request.session.pop(self.SESSION_KEY, None)
        logger.info('Clave restablecida para la cuenta %s.', user.pk)

        # Si quien la cambio tiene sesion abierta con esa misma cuenta, se
        # mantiene: cambiar la clave invalida el hash de la sesion.
        if request.user.is_authenticated and request.user.pk == user.pk:
            update_session_auth_hash(request, user)

        messages.success(request, _(
            'Your password has been reset successfully. '
            'You can now log in with your new password.'
        ))

        return redirect('account:login')


class ChangePasswordFormView(FormView):
    """
    Cambiar la clave, para quien ya tiene sesion.

    Exige la clave actual, y sus fallos **cuentan en el mismo freno** que los
    del acceso: una sesion robada no puede servir para adivinar la clave desde
    aqui sin limite, que es lo que pasaria si esta pantalla no apuntara nada.
    """

    template_name = 'account/change_password.html'
    form_class = ChangePasswordForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _(
                'You must be logged in to change your password.'))
            return redirect_to_login(request.get_full_path())

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if is_locked_out(request, request.user.get_username()):
            messages.error(request, _(
                'Too many failed attempts. Please wait before trying again.'))
            return redirect('account:change_password')

        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()

        # Sin esto, cambiar la clave cierra la sesion de quien acaba de
        # cambiarla: el hash de la sesion depende de la clave.
        update_session_auth_hash(self.request, user)

        messages.success(self.request, _(
            'Your password has been changed successfully!'))

        return redirect('core:index')

    def form_invalid(self, form):
        if 'old_password' in form.errors:
            note_failure(
                self.request, self.request.user.get_username(),
                reason='change password',
            )

        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Change Password')
        return context

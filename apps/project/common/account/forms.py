from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.project.common.users.validators import (
    UnicodeLastNameValidator,
    UnicodeNameValidator,
    UnicodeUsernameValidator
)

UserModel = get_user_model()
USER_OR_EMAIL_TXT = _('User or Email')
PASSWORD_TXT = _('Password')
USER_TXT = _('User')
EMAIL_TXT = _('Email')

class UserRegisterForm(forms.ModelForm):
    username_validator = UnicodeUsernameValidator()
    name_validator = UnicodeNameValidator()
    last_name_validator = UnicodeLastNameValidator()

    username = forms.CharField(
        label=USER_TXT,
        validators=[username_validator],
        required=True,
        widget=forms.TextInput(
            attrs={
                "id": "register_username",
                "type": "text",
                "placeholder": USER_TXT,
                "class": "form-control",
                'aria-label': USER_TXT,
                'aria-describedby': 'register_username'
            }
        )
    )

    email = forms.CharField(
        label=EMAIL_TXT,
        required=True,
        widget=forms.EmailInput(
            attrs={
                "id": "register_email",
                "type": "email",
                "placeholder": EMAIL_TXT,
                "class": "form-control",
                'aria-label': EMAIL_TXT,
                'aria-describedby': 'register_email'
            }
        )
    )

    password = forms.CharField(
        label=PASSWORD_TXT,
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "id": "register_password",
                'type': 'password',
                'placeholder': PASSWORD_TXT,
                'class': 'form-control',
                'aria-label': PASSWORD_TXT,
                'aria-describedby': 'register_password'
            }
        )
    )

    confirm_password = forms.CharField(
        label=_('Confirm Password'),
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "id": "register_confirm_password",
                "type": "password",
                "placeholder": _('Confirm Password'),
                "class": "form-control",
                'aria-label': _('Confirm Password'),
                'aria-describedby': 'register_confirm_password'
            }
        )
    )

    first_name = forms.CharField(
        label=_("Names"),
        required=True,
        validators=[name_validator],
        widget=forms.TextInput(
            attrs={
                "id": "register_first_name",
                "type": "text",
                "placeholder": _("Names"),
                "class": "form-control",
                'aria-label': _('Names'),
                'aria-describedby': 'register_first_name'
            }
        )
    )

    last_name = forms.CharField(
        label=_("Last names"),
        required=True,
        validators=[last_name_validator],
        widget=forms.TextInput(
            attrs={
                "id": "register_last_name",
                "type": "text",
                "placeholder": _("Last names"),
                "class": "form-control",
                'aria-label': _('Last names'),
                'aria-describedby': 'register_last_name'
            }
        )
    )

    def clean_confirm_password(self):
        validate_password(
            self.cleaned_data["password"],
        )

        validate_password(
            self.cleaned_data["confirm_password"],
        )

        if self.cleaned_data["password"] != self.cleaned_data["confirm_password"]:
            raise ValidationError(_('Passwords do not match'))

    class Meta:
        model = UserModel
        fields = (
            "username",
            "email",
            "first_name",
            "last_name"
        )


class UserUpdateProfile(forms.ModelForm):
    pass


class LoginOTPForm(forms.Form):
    """
    La entrada por codigo: a quien, y que codigo.

    Un solo formulario con los dos campos, no dos pantallas seguidas. La
    pantalla ensena el identificador y el codigo a la vez, con un boton que
    manda el correo y otro que entra; quien llega a ella ya sabe que le van a
    pedir y no descubre a mitad de camino que habia un segundo paso.

    El envio del codigo **no** pasa por aqui: lo atiende la vista antes de
    validar nada, porque exigir un codigo para poder pedirlo seria un circulo.

    No comprueba que la cuenta exista, y no es un descuido: contestar «no
    existe» convertiria la pantalla en un comprobador de cuentas. Quien la
    rellena ve siempre lo mismo, y el correo solo sale si hay a quien
    mandarselo.
    """

    identifier = forms.CharField(
        label=USER_OR_EMAIL_TXT,
        max_length=254,
        widget=forms.TextInput(
            attrs={
                'id': 'id_otp-identifier',
                'class': 'form-control',
                'autocomplete': 'username',
                'placeholder': ' ',
                'aria-label': USER_OR_EMAIL_TXT,
            }
        ),
    )

    code = forms.CharField(
        label=_('Verification code'),
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                'id': 'id_otp-code',
                # Las clases van en el widget y no en un filtro de plantilla:
                # poner `class` alli reemplaza el atributo entero y se
                # llevaria por delante el centrado y el espaciado.
                'class': 'form-control text-center fs-4 fw-semibold',
                'style': 'letter-spacing:.4em;',
                'autocomplete': 'one-time-code',
                'inputmode': 'numeric',
                'pattern': '[0-9]*',
                'maxlength': '6',
                'placeholder': ' ',
                'aria-label': _('Verification code'),
            }
        ),
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user_cache = None

    def clean_identifier(self):
        return (self.cleaned_data['identifier'] or '').strip().lower()

    def clean_code(self):
        return (self.cleaned_data['code'] or '').strip()

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get('code')
        identifier = cleaned.get('identifier') or ''

        if not code:
            return cleaned

        from apps.common.utils.login_attempts import is_locked_out, note_failure

        from .otp_login import verify

        # Se pregunta por el bloqueo **antes** de mirar el codigo. Al reves se
        # apuntarian los fallos sin frenar nada, que es tanto como no tener
        # freno: el tope de cinco intentos por codigo se esquiva pidiendo otro.
        if is_locked_out(self.request, identifier):
            raise ValidationError(
                _('Too many failed attempts. Please wait before trying again.')
            )

        self.user_cache = verify(self.request, code)

        if self.user_cache is None:
            # Un codigo equivocado cuenta igual que una contrasena equivocada.
            # Sin esto, probar codigos de seis cifras sale gratis y el freno de
            # la contrasena solo estorba a quien de verdad la olvido.
            note_failure(self.request, identifier, reason='login otp')

            # El mismo mensaje para un codigo equivocado, uno caducado y uno
            # que nunca se emitio. Distinguirlos diria si la cuenta existe.
            raise ValidationError(
                _('The code is not valid or has expired. Request a new one.')
            )

        return cleaned

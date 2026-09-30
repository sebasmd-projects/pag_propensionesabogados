"""
El formulario de la entrada por codigo: a quien, y que codigo.

Vive en su propio modulo, como en GEA. Lo usa el paso `otp` del asistente de
acceso (`login_view.py`).
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

USER_OR_EMAIL_TXT = _('User or Email')


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

        from ..otp_login import verify

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

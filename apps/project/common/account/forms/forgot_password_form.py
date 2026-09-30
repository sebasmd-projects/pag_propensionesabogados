"""
Los dos formularios de "olvide mi contrasena".

Paso 1: a quien se le manda el enlace. Paso 2: la clave nueva.

El paso 1 **no comprueba que la cuenta exista** y no es un descuido: contestar
"no existe" convertiria la pantalla en un comprobador de cuentas. Quien lo
rellena ve siempre lo mismo; el correo solo sale si hay a quien mandarselo
(ver `views.ForgotPasswordFormView`).
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

UserModel = get_user_model()


class ForgotPasswordStep1Form(forms.Form):
    """Paso 1: el usuario o el correo de la cuenta."""

    email_or_username = forms.CharField(
        label=_('Email or Username'),
        required=True,
        max_length=254,
        widget=forms.TextInput(attrs={
            'id': 'forgot_email_username',
            'type': 'text',
            'placeholder': ' ',
            'class': 'form-control',
            'autocomplete': 'username',
        }),
    )

    def clean_email_or_username(self):
        value = (self.cleaned_data.get('email_or_username') or '').strip().lower()

        if not value:
            raise ValidationError(_('This field is required.'))

        return value

    def get_users(self):
        """
        Las cuentas a las que corresponde el texto tecleado.

        Solo activas y con contrasena utilizable: a una cuenta dada de baja no
        se le manda un enlace que no le va a servir.

        Puede haber mas de una: el modelo exige que la pareja (usuario, correo)
        sea unica, no el correo solo. Se devuelven todas, que es lo que hace el
        restablecimiento de Django, porque elegir una seria adivinar.
        """
        value = (self.cleaned_data.get('email_or_username') or '').strip()

        if not value:
            return []

        lookup = (
            {'email__iexact': value}
            if '@' in value
            else {'username__iexact': value}
        )

        return [
            user
            for user in UserModel._default_manager.filter(
                is_active=True, **lookup
            )
            if user.has_usable_password()
        ]


class ForgotPasswordStep2Form(SetPasswordForm):
    """Paso 2: la clave nueva y su confirmacion, con los validadores de Django."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        self.fields['new_password1'].label = _('New Password')
        self.fields['new_password1'].widget = forms.PasswordInput(attrs={
            'id': 'new_password1',
            'placeholder': ' ',
            'class': 'form-control',
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].label = _('Confirm New Password')
        self.fields['new_password2'].widget = forms.PasswordInput(attrs={
            'id': 'new_password2',
            'placeholder': ' ',
            'class': 'form-control',
            'autocomplete': 'new-password',
        })

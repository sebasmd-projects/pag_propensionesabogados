"""
El formulario de "cambiar contrasena", para quien ya tiene sesion.

Exige la clave actual: una sesion abierta en un equipo ajeno no debe bastar
para quedarse con la cuenta.
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _


class ChangePasswordForm(forms.Form):

    old_password = forms.CharField(
        label=_('Current Password'),
        widget=forms.PasswordInput(attrs={
            'id': 'old_password',
            'placeholder': ' ',
            'class': 'form-control',
            'autocomplete': 'current-password',
        }),
        strip=False,
    )

    new_password1 = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={
            'id': 'new_password1',
            'placeholder': ' ',
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
        strip=False,
    )

    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={
            'id': 'new_password2',
            'placeholder': ' ',
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
        strip=False,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')

        if not self.user.check_password(old_password):
            raise forms.ValidationError(
                _('Your current password was entered incorrectly.'))

        return old_password

    def clean(self):
        cleaned = super().clean()

        old_password = cleaned.get('old_password')
        new_password1 = cleaned.get('new_password1')
        new_password2 = cleaned.get('new_password2')

        if new_password1 and new_password2 and new_password1 != new_password2:
            self.add_error(
                'new_password2', _("The two password fields didn't match."))

        elif new_password1:
            if old_password and new_password1 == old_password:
                self.add_error('new_password1', _(
                    'New password cannot be the same as current password.'))
            else:
                # Los validadores de Django, con el usuario delante para que
                # `UserAttributeSimilarityValidator` sepa contra que comparar.
                try:
                    validate_password(new_password1, self.user)
                except forms.ValidationError as error:
                    self.add_error('new_password1', error)

        return cleaned

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password1'])

        if commit:
            self.user.save()

        return self.user

"""
Los formularios de la cuenta, uno por modulo.

Todo lo que se importaba de `account.forms` sigue importandose de aqui.

No estan `buyers_register_form`, `suppliers_register_form` ni
`common_register_form` de GEA: dependen de campos de usuario que esta casa no
tiene (`user_type`, documento de identidad, KYC...) y el registro de aqui es
el de siempre (`register_form.py`).
"""

from .change_password_form import ChangePasswordForm
from .forgot_password_form import ForgotPasswordStep1Form, ForgotPasswordStep2Form
from .login_otp_form import LoginOTPForm
from .register_form import UserRegisterForm, UserUpdateProfile

__all__ = [
    'ChangePasswordForm',
    'ForgotPasswordStep1Form',
    'ForgotPasswordStep2Form',
    'LoginOTPForm',
    'UserRegisterForm',
    'UserUpdateProfile',
]

"""
Las rutas de la cuenta.

Las rutas del segundo factor no estan aqui sino en `two_factor_urls.py`, y no
por capricho: incluirlas desde este fichero las habria dejado **anidadas**
bajo el espacio de nombres de la aplicacion, o sea como
`account:two_factor:login`, y ni la biblioteca ni `django-otp` las buscan asi.
Se cuelgan del raiz, que es donde esperan encontrarlas.
"""

from django.urls import path

from .login_view import PropensionesLoginView
from .views import (
    ChangePasswordFormView,
    ForgotPasswordFormView,
    UserLogoutView,
    UserRegisterView,
)

app_name = "account"

urlpatterns = [
    path(
        'accounts/login/',
        PropensionesLoginView.as_view(),
        name='login'
    ),
    path(
        'accounts/register/',
        UserRegisterView.as_view(),
        name='register'
    ),
    path(
        'accounts/logout/',
        UserLogoutView.as_view(),
        name='logout'
    ),
    # Los nombres son los de GEA; el camino cuelga de `accounts/`, como el
    # resto de la cuenta aqui.
    path(
        'accounts/change/password/',
        ChangePasswordFormView.as_view(),
        name='change_password'
    ),
    path(
        'accounts/forgot/password/',
        ForgotPasswordFormView.as_view(),
        name='forgot_password'
    ),
]

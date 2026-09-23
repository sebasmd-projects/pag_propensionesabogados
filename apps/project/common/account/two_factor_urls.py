"""
Las rutas de `django-two-factor-auth`, con el acceso apuntando a esta casa.

Por que no se incluye `two_factor.urls` tal cual
------------------------------------------------
Porque esa lista registra **su** vista de acceso bajo el nombre
`two_factor:login`, que es el que buscan la propia biblioteca y `django-otp`
cuando mandan a identificarse a quien no lo esta. Incluirla dejaria el sitio
con dos pantallas de acceso: la de aqui, con el codigo al correo y el freno
de `axes`, y la de la biblioteca, sin ninguna de las dos.

Se rehace la lista con las mismas vistas salvo el acceso. El resto --dar de
alta el segundo factor, el QR, los codigos de respaldo, quitarlo-- son las de
la biblioteca sin tocar: no hay nada en ellas que el proyecto necesite
cambiar.

Y va fuera de `urls.py` porque aquel declara `app_name = "account"`: incluir
esto desde alli habria anidado los nombres --`account:two_factor:login`-- y
entonces nadie los encontraria.

Los caminos empiezan por `accounts/` y no por `account/`, que es lo que trae
la biblioteca, porque `accounts/` es el que ya usaba el sitio y cambiarlo
romperia los enlaces escritos por ahi.
"""

from django.urls import path
from two_factor.views import (
    BackupTokensView,
    DisableView,
    ProfileView,
    QRGeneratorView,
    SetupCompleteView,
    SetupView,
)

from .login_view import PropensionesLoginView

app_name = 'two_factor'

urlpatterns = [
    path(
        'accounts/login/',
        PropensionesLoginView.as_view(),
        name='login'
    ),
    path(
        'accounts/two_factor/setup/',
        SetupView.as_view(),
        name='setup'
    ),
    path(
        'accounts/two_factor/qrcode/',
        QRGeneratorView.as_view(),
        name='qr'
    ),
    path(
        'accounts/two_factor/setup/complete/',
        SetupCompleteView.as_view(),
        name='setup_complete'
    ),
    path(
        'accounts/two_factor/backup/tokens/',
        BackupTokensView.as_view(),
        name='backup_tokens'
    ),
    path(
        'accounts/two_factor/',
        ProfileView.as_view(),
        name='profile'
    ),
    path(
        'accounts/two_factor/disable/',
        DisableView.as_view(),
        name='disable'
    ),
]

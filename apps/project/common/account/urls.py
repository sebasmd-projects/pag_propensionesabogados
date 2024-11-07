from django.urls import path

from .views import UserLoginView, UserLogoutView, UserRegisterView

app_name = "account"

urlpatterns = [
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
    path(
        'accounts/login/',
        UserLoginView.as_view(),
        name='login'
    )
]

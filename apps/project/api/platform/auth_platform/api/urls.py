# apps/project/api/platform/auth_platform/api/urls.py

from django.urls import path
from .views import AttlasInsolvencyAuthLoginAPIView, AttlasInsolvencyAuthRegisterAPIView, TokenInfoAPIView

urlpatterns = [
    path(
        'login/',
        AttlasInsolvencyAuthLoginAPIView.as_view(),
        name='api-insolvency-login'
    ),
    path(
        'register/',
        AttlasInsolvencyAuthRegisterAPIView.as_view(),
        name='api-insolvency-register'
    ),
    path(
        'token-info/',
        TokenInfoAPIView.as_view(),
        name='token-info'
    )
]

# apps/project/api/platform/auth_platform/api/urls.py

from django.urls import path
from .views import (
    AttlasInsolvencyAuthLoginAPIView,
    AttlasInsolvencyAuthRegisterAPIView,
    TokenInfoAPIView,
    AttlasInsolvencyAuthConsultantsRegisterAPIView,
    ClientSearchView
)

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
        'clients/search/',
        ClientSearchView.as_view(),
        name='api-calc-client-search'
    ),
    path(
        'register-consultants/',
        AttlasInsolvencyAuthConsultantsRegisterAPIView.as_view(),
        name='api-insolvency-consultants-register'
    ),
    path(
        'token-info/',
        TokenInfoAPIView.as_view(),
        name='token-info'
    )
]

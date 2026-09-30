# apps/project/api/platform/auth_platform/api/urls.py

from django.urls import path
from .views import (
    AttlasInsolvencyAuthLoginAPIView,
    AttlasInsolvencyAuthRegisterAPIView,
    TokenInfoAPIView,
    AttlasInsolvencyAuthConsultantsRegisterAPIView,
    ClientSearchView,
    ClientLookupView,
    ClientLookupVerifyView,
)

urlpatterns = [
    path("clients/lookup/", ClientLookupView.as_view(), name="api-clients-lookup"),
    path("clients/lookup/verify/", ClientLookupVerifyView.as_view(), name="api-clients-lookup-verify"),
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

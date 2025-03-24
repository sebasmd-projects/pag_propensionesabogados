from django.urls import path
from .views import AttlasInsolvencyAuthLoginAPIView, AttlasInsolvencyAuthRegisterAPIView

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
    )
]

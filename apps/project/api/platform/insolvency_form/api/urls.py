#  apps/project/api/platform/insolvency_form/api/urls.py

from django.urls import path
from .views import AttlasInsolvencyFormAPIView

urlpatterns = [
    path(
        'insolvency-form/',
        AttlasInsolvencyFormAPIView.as_view(),
        name='api-insolvency-form'
    )
]

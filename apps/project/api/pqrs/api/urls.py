from django.urls import path
from .views import PQRSModelCreateAPIView

urlpatterns = [
    path(
        'pqrs/',
        PQRSModelCreateAPIView.as_view(),
        name='api-pqrs-create'
    ),
]

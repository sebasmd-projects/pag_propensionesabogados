from django.urls import path
from .views import ContactCreateAPIView

urlpatterns = [
    path(
        'contact/',
        ContactCreateAPIView.as_view(),
        name='api-contact-create'
    ),
]

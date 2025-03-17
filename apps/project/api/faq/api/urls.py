from django.urls import path
from .views import MainFAQListAPIView, OtherFAQListAPIView

urlpatterns = [
    path(
        'main-faq/',
        MainFAQListAPIView.as_view(),
        name='api-main-faq-list'
    ),
    path(
        'other-faq/',
        OtherFAQListAPIView.as_view(),
        name='api-other-faq-list'
    ),
]

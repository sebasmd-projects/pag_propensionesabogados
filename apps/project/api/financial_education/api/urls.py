from django.urls import path
from .views import FinancialEducationListAPIView

urlpatterns = [
    path(
        'financial-education/',
        FinancialEducationListAPIView.as_view(),
        name='api-financial-education-list'
    ),
]

#  apps/project/api/platform/insolvency_form/api/urls.py

from django.urls import path

from .views import InsolvencyFormWizardView, SignatureUpdateView, SignatureCreateAPIView

app_name = 'insolvency_form_api'

urlpatterns = [
    path(
        'insolvency-form/<uuid:id>/',
        InsolvencyFormWizardView.as_view(),
        name='wizard'
    ),
    path(
        'insolvency-form/',
        InsolvencyFormWizardView.as_view(),
        name='wizard-me'
    ),
    path(
        'insolvency-form/signature/<uuid:id>/',
        SignatureUpdateView.as_view(),
        name='signature-update'
    ),
    path(
        'insolvency-form/signature/',
        SignatureCreateAPIView.as_view(),
        name='signature-create'
    ),
]

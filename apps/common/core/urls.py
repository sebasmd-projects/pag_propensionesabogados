from django.urls import path

from apps.common.core.views import (DocumentsView, IndexTemplateView,
                                    PrivacyPolicyView, TermsAndConditionsView)

app_name = 'core'

urlpatterns = [
    path(
        '',
        IndexTemplateView.as_view(),
        name='index'
    ),
    path(
        'terms-and-conditions/',
        TermsAndConditionsView.as_view(),
        name='terms_and_conditions'
    ),
    path(
        'privacy-policy/',
        PrivacyPolicyView.as_view(),
        name='privacy_policy'
    ),
    path(
        'documents/',
        DocumentsView.as_view(),
        name='documents'
    )
]

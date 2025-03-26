from django.urls import path

from apps.common.core.views import (DocumentsView, IndexTemplateView,
                                    PrivacyPolicyView, TermsAndConditionsView,
                                    security_txt_view)

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
    ),
    path(
        '.well-known/security.txt',
        security_txt_view,
        name='security_txt'
    ),
]

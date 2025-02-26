from django.urls import path, include

from apps.common.core.views import (IndexTemplateView, PrivacyPolicyView,
                                    TermsAndConditionsView)

from .api import urls as api_urls

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
        'api/v1/',
        include(api_urls.urlpatterns)
    ),
]

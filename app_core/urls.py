import importlib.util

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from apps.common.utils.views import handler400 as h400
from apps.common.utils.views import handler403 as h403
from apps.common.utils.views import handler404 as h404
from apps.common.utils.views import handler500 as h500

admin_url = settings.ADMIN_URL
custom_apps = settings.CUSTOM_APPS
utils_path = settings.UTILS_PATH

apps_urls = [path('', include(f'{app}.urls')) for app in custom_apps]

api_urls = [
    path('api/v1/', include(f'{app}.api.urls'))
    for app in custom_apps
    if importlib.util.find_spec(f'{app}.api') is not None
]

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="Propensiones Abogados and Fundación Attlas API",
        terms_of_service="https://fundacionattlas.org/es/documentos/legales/terminos-y-condiciones",
        contact=openapi.Contact(email="support@propensionesabogados.com"),
    ),
    public=False,
    permission_classes=(
        permissions.IsAuthenticated,
        permissions.IsAdminUser
    ),
)

handler400 = h400

handler403 = h403

handler404 = h404

handler500 = h500

third_party_urls = [
    re_path(
        r'^rosetta/',
        include('rosetta.urls')
    ),
]

admin_urls = [
    path(admin_url, admin.site.urls),
    path('_nested_admin/', include('nested_admin.urls')),
]

ckeditor_urls = [
    path("ckeditor5/", include('django_ckeditor_5.urls')),
]

drf_yasg_urls = [
    path(
        'api/drf_yasg<format>/',
        schema_view.without_ui(
            cache_timeout=0
        ),
        name='schema-json'
    ),
    path(
        'api/swagger/',
        schema_view.with_ui(
            'swagger',
            cache_timeout=0
        ),
        name='schema-swagger-ui'
    ),
    path(
        'api/redoc/',
        schema_view.with_ui(
            'redoc',
            cache_timeout=0
        ),
        name='schema-redoc'
    ),
]

urlpatterns = admin_urls + apps_urls + drf_yasg_urls + api_urls + ckeditor_urls + third_party_urls

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

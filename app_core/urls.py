from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from apps.common.utils.views import handler400 as h400
from apps.common.utils.views import handler403 as h403
from apps.common.utils.views import handler404 as h404
from apps.common.utils.views import handler500 as h500

admin_url = settings.ADMIN_URL
custom_apps = settings.CUSTOM_APPS
utils_path = settings.UTILS_PATH

apps_urls = [path('', include(f'{app}.urls')) for app in custom_apps]

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
]

urlpatterns = admin_urls + apps_urls + third_party_urls

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
from django.urls import path

from .views import PazYSalvoView, PublicCaseQueryView

app_name = 'case_manager'

urlpatterns = [
    path(
        'consultar/proceso/',
        PublicCaseQueryView.as_view(),
        name='public_query'
    ),
    path(
        'consultar/proceso/<uuid:pk>/paz-y-salvo/',
        PazYSalvoView.as_view(),
        name='paz_y_salvo'
    ),
]

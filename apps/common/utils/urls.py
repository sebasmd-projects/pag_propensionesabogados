from django.conf import settings
import re

from django.http import HttpResponse
from django.urls import path

from .attack_patterns import common_attack_paths
from .csp_report import csp_report
from .views import set_language


def simplify_regex(pattern):
    pattern = re.sub(
        r'\[\^*\]\.\*\?*',
        '',
        pattern
    )
    pattern = re.sub(
        r'\[([A-Za-z])([A-Za-z])\]',
        lambda m: m.group(1).upper(),
        pattern
    )
    pattern = re.sub(
        r'[^a-zA-Z0-9]',
        '',
        pattern
    )
    return pattern


def robots_txt(request):
    lines = ["User-agent: *"]

    attack_terms = sorted(set(settings.COMMON_ATTACK_TERMS))
    for term in attack_terms:
        if term:
            lines.append(f"Disallow: /{term.strip('/')}")

    return HttpResponse("\n".join(lines), content_type="text/plain")


utils_path = [
    path('robots.txt', robots_txt),
    path('set_language/', set_language, name='set_language'),
    # Destino de `report-uri` de la CSP en modo solo informe. Sin barra
    # inicial: el prefijo de la app lo pone `app_core/urls.py`.
    path('csp-report/', csp_report, name='csp_report'),
]

urlpatterns = common_attack_paths + utils_path

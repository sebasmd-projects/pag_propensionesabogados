import re

from django.http import HttpResponse
from django.urls import path

from .attack_patterns import common_attack_paths
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
    lines = [
        "User-agent: *",
        "Disallow: /*",
        "Disallow: /",
    ]

    for pattern in common_attack_paths:
        if hasattr(pattern, 'pattern'):
            url_text = simplify_regex(pattern.pattern.describe())
            if url_text:
                lines.append(f"Disallow: /{url_text}")
    return HttpResponse("\n".join(lines), content_type="text/plain")


utils_path = [
    path('robots.txt', robots_txt),
    path('set_language/', set_language, name='set_language'),
]

urlpatterns = common_attack_paths + utils_path

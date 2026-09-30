"""Toda apertura de la API debe ser una decisión explícita y revisable."""
from itertools import product
from uuid import uuid4

from django.core.cache import cache
from django.test import override_settings
from django.urls import URLResolver, get_resolver, resolve
from django.utils.regex_helper import normalize
from rest_framework.test import APITestCase


PUBLIC_API_ROUTES = {
    'api-contact-create': 'Formulario de contacto para visitantes sin cuenta.',
    'api-pqrs-create': 'Recepción pública de peticiones, quejas, reclamos y sugerencias.',
    'api-main-faq-list': 'Preguntas frecuentes públicas del sitio.',
    'api-other-faq-list': 'Preguntas frecuentes adicionales públicas del sitio.',
    'api-financial-education-list': 'Contenido público de educación financiera.',
}


def sample_segment(pattern):
    """Materializa cada patrón; falla si un tipo nuevo necesita otro ejemplo."""
    template, parameters = normalize(pattern.regex.pattern)[0]
    choices = []
    for name in parameters:
        converter = getattr(pattern, 'converters', {}).get(name)
        kind = type(converter).__name__
        candidates = {'IntConverter': ('1',), 'SlugConverter': ('x',),
                      'StringConverter': ('x',), 'PathConverter': ('x',),
                      'UUIDConverter': (str(uuid4()),)}.get(kind, ('x', '1', str(uuid4())))
        valid = []
        for candidate in candidates:
            if converter is not None:
                try:
                    converter.to_python(candidate)
                except (ValueError, TypeError):
                    continue
            valid.append(candidate)
        choices.append(valid)
    for candidates in product(*choices):
        segment = template % dict(zip(parameters, candidates))
        if pattern.regex.fullmatch(segment):
            return segment
    raise AssertionError(f'No se pudo materializar {pattern}; añade un ejemplo válido')


def api_routes(patterns=None, parents=(), namespaces=()):
    if patterns is None:
        patterns = get_resolver().url_patterns
    for entry in patterns:
        chain = parents + (entry.pattern,)
        if isinstance(entry, URLResolver):
            nested = namespaces + ((entry.namespace,) if entry.namespace else ())
            yield from api_routes(entry.url_patterns, chain, nested)
        elif ''.join(normalize(p.regex.pattern)[0][0] for p in chain).startswith('api/'):
            path = ''.join(sample_segment(p) for p in chain)
            name = ':'.join(namespaces + (entry.name,)) if entry.name else None
            yield '/' + path, name, entry.callback


@override_settings(SECURE_SSL_REDIRECT=False, ATTLAS_SERVER_KEY='x' * 40)
class APIOpenRoutesTests(APITestCase):
    def test_anonymous_routes_require_explicit_allowlist(self):
        routes = list(api_routes())
        self.assertTrue(routes)
        for url, name, callback in routes:
            with self.subTest(url=url, name=name):
                cache.clear()
                self.assertIs(resolve(url).func, callback)
                view = getattr(callback, 'cls', None)
                actions = getattr(callback, 'actions', None)
                supports_get = ('get' in actions if actions is not None else
                                view is None or ('get' in view.http_method_names and hasattr(view, 'get')))
                response = (self.client.get(url) if supports_get else
                            self.client.post(url, {}, format='json'))
                if name in PUBLIC_API_ROUTES:
                    self.assertIn(response.status_code, (200, 201, 202, 204, 400))
                else:
                    self.assertIn(response.status_code, (401, 403),
                                  f'{name} está abierta sin justificación: {response.status_code}')

    def test_allowlist_has_no_removed_routes(self):
        names = {name for _, name, _ in api_routes()}
        self.assertFalse(PUBLIC_API_ROUTES.keys() - names)

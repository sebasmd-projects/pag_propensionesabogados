"""
Endurecimiento de la respuesta: CORS enumerado, CSP en modo solo informe y
cookies/subidas explicitas.

Se prueba **pidiendo paginas** con el cliente de pruebas, no leyendo los
settings: lo que importa es lo que sale por la red.
"""

import base64
from io import StringIO

from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.project.api.platform.case_manager.choices import Service, Stage
from apps.project.api.platform.case_manager.models import CaseModel, ClientModel
from apps.project.api.platform.case_manager.tests.test_access import (
    login_as, make_user)
from apps.project.api.platform.case_manager.tests.test_public_access import (
    identificarse)

REPORT_ONLY = 'Content-Security-Policy-Report-Only'

# Los seis del hallazgo n.º 4, con y sin www. Ni uno mas, ni uno menos.
CORS_ESPERADOS = [
    'https://geausa.propensionesabogados.com',
    'https://www.geausa.propensionesabogados.com',
    'https://fundacionattlas.com',
    'https://www.fundacionattlas.com',
    'https://fundacionattlas.org',
    'https://www.fundacionattlas.org',
]


def directives(policy: str) -> dict:
    """`'a b; c d'` -> `{'a': ['b'], 'c': ['d']}`."""
    out = {}
    for part in policy.split(';'):
        tokens = part.split()
        if tokens:
            out[tokens[0]] = tokens[1:]
    return out


class CorsTests(TestCase):
    """Un origen enumerado recibe la cabecera; un subdominio cualquiera, no."""

    def setUp(self):
        cache.clear()

    def _get(self, origin):
        return self.client.get(
            reverse('api-main-faq-list'), HTTP_ORIGIN=origin)

    def test_la_lista_por_defecto_son_exactamente_esos_seis(self):
        self.assertEqual(
            settings.CORS_ALLOWED_ORIGINS_DEFAULT, CORS_ESPERADOS)

    def test_no_queda_ningun_comodin_de_subdominio(self):
        self.assertFalse(getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', []))

    @override_settings(CORS_ALLOWED_ORIGINS=CORS_ESPERADOS)
    def test_un_origen_permitido_recibe_allow_origin(self):
        for origin in CORS_ESPERADOS:
            with self.subTest(origin=origin):
                response = self._get(origin)
                self.assertEqual(
                    response.headers.get('Access-Control-Allow-Origin'),
                    origin)

    @override_settings(CORS_ALLOWED_ORIGINS=CORS_ESPERADOS)
    def test_un_subdominio_cualquiera_no_lo_recibe(self):
        for origin in (
            'https://abandonado.propensionesabogados.com',
            'https://evil.fundacionattlas.org',
            'https://fundacionattlas.org.evil.com',
            'http://fundacionattlas.org',
        ):
            with self.subTest(origin=origin):
                response = self._get(origin)
                self.assertNotIn(
                    'Access-Control-Allow-Origin', response.headers)


class CspHeaderTests(TestCase):
    """Las respuestas llevan la CSP en modo solo informe, y solo informe."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cls.client_record = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test')
        cls.case = CaseModel.objects.create(
            client=cls.client_record, service=Service.JUDICIAL,
            stage=Stage.FINISHED, paz_y_salvo_authorized=True)

    def setUp(self):
        cache.clear()

    def assertReportOnly(self, response):
        self.assertLess(response.status_code, 400, response.status_code)
        self.assertIn(REPORT_ONLY, response.headers)
        # Modo informe: NUNCA la cabecera que bloquea.
        self.assertNotIn('Content-Security-Policy', response.headers)
        return directives(response.headers[REPORT_ONLY])

    def test_sitio_publico(self):
        policy = self.assertReportOnly(self.client.get('/'))

        self.assertEqual(policy['default-src'], ["'self'"])
        # Lo que cargan las plantillas, origen por origen.
        self.assertIn('https://fonts.googleapis.com', policy['style-src'])
        self.assertIn('https://fonts.gstatic.com', policy['font-src'])
        self.assertIn('https://cdn.jsdelivr.net', policy['script-src'])
        self.assertIn('https://cdn.datatables.net', policy['script-src'])
        self.assertIn('https://cdn.datatables.net', policy['style-src'])
        self.assertIn('https://tracecertificates.com', policy['img-src'])
        self.assertIn(
            'https://www.google.com/recaptcha/', policy['script-src'])
        self.assertIn(
            'https://www.google.com/recaptcha/', policy['frame-src'])
        self.assertEqual(policy['report-uri'], [settings.CSP_REPORT_PATH])

    def test_script_src_no_admite_scripts_en_linea(self):
        """Todavia no se pasa a modo efectivo: asi salen en los informes."""
        policy = self.assertReportOnly(self.client.get('/'))

        self.assertNotIn("'unsafe-inline'", policy['script-src'])
        self.assertNotIn("'unsafe-eval'", policy['script-src'])

    def test_cuenta(self):
        self.assertReportOnly(self.client.get(reverse('account:login')))

    def test_gestor(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

        self.assertReportOnly(
            self.client.get(reverse('case_manager:gestor_dashboard')))

    def test_portal(self):
        self.assertReportOnly(
            self.client.get(reverse('case_manager:public_query')))

    def test_paz_y_salvo(self):
        identificarse(self.client, '16484186')

        response = self.client.get(
            reverse('case_manager:paz_y_salvo', args=[self.case.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertReportOnly(response)

    def test_el_punto_de_informes_esta_en_la_ruta_de_la_politica(self):
        self.assertEqual(reverse('csp_report'), settings.CSP_REPORT_PATH)


class CookiesAndUploadsTests(TestCase):
    """Lo que antes era el defecto de Django, ahora escrito."""

    def test_la_cookie_de_sesion_no_la_lee_javascript(self):
        self.assertIs(settings.SESSION_COOKIE_HTTPONLY, True)

    def test_samesite_lax_en_sesion_y_csrf(self):
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, 'Lax')

    def test_la_cookie_de_sesion_sale_con_httponly_y_samesite(self):
        # El cliente de pruebas arma la cookie a mano al hacer login; la que
        # cuenta es la que pone el middleware de sesion en una respuesta real.
        middleware = SessionMiddleware(lambda request: HttpResponse())
        request = RequestFactory().get('/')
        middleware.process_request(request)
        request.session['x'] = 1

        response = middleware.process_response(request, HttpResponse())
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]

        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')

    def test_topes_de_subida(self):
        self.assertEqual(
            settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 5 * 1024 * 1024)
        self.assertEqual(settings.DATA_UPLOAD_MAX_NUMBER_FILES, 20)

    def test_una_firma_de_attlas_cabe_con_holgura(self):
        # Medida: un garabato denso a 3000 px de ancho, en base64, ronda los
        # 75 KB. Aqui se usa 300 KB, cuatro veces mas.
        firma = base64.b64encode(b'\x89PNG' + b'x' * 300_000).decode()

        self.assertLess(len(firma) * 10, settings.DATA_UPLOAD_MAX_MEMORY_SIZE)

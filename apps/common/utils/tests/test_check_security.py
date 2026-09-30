# apps/common/utils/tests/test_check_security.py
"""
``check_security`` y ``check_health``: que digan lo que dicen decir.

Una comprobacion de seguridad que no falla nunca es peor que no tenerla: da
una tranquilidad que nadie ha ganado. Aqui se comprueba que cada seccion **se
queja cuando debe** --una vista nueva sin guardia, un formulario sin freno, una
clave corta, un origen con comodin--, no solo que el repositorio, tal como
esta, sale limpio.

    manage.py test apps.common.utils.tests.test_check_security \\
        --settings=app_core.settings_test
"""

import json
import urllib.error
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from app_core.tests.test_api_open_routes import PUBLIC_API_ROUTES

from ..management.commands import check_health, check_security
from ..management.commands.check_security import (INTENTIONALLY_PUBLIC,
                                                  THROTTLED_FORMS, Command)


def run_check_security(**options):
    out = StringIO()

    try:
        call_command('check_security', stdout=out, **options)
    except SystemExit as stop:
        out.write(f'\n[exit {stop.code}]')

    return out.getvalue()


def section(report, number):
    """El texto de una seccion numerada del informe."""
    start = report.index(f'\n{number}. ')
    following = report.find(f'\n{number + 1}. ', start)

    return report[start:following if following > 0 else None]


class ThePublicListsAgreeTests(SimpleTestCase):

    def test_the_public_api_routes_are_the_ones_the_route_test_allows(self):
        """
        Hay dos listas de rutas de la API publicas a proposito: la de aqui y la
        de `app_core/tests/test_api_open_routes.py`, que ademas las llama sin
        credenciales. Si una discrepa de la otra, una de las dos miente.
        """
        api_here = {
            name for name in INTENTIONALLY_PUBLIC if name.startswith('api-')}

        self.assertEqual(api_here, set(PUBLIC_API_ROUTES))

    def test_every_public_entry_says_why(self):
        for label, reason in INTENTIONALLY_PUBLIC.items():
            self.assertGreater(len(reason), 15, f'{label} sin explicar por que')

    def test_every_throttled_form_is_a_public_route(self):
        """Un formulario a vigilar que no esta en la lista de publicas sobra."""
        self.assertLessEqual(THROTTLED_FORMS, set(INTENTIONALLY_PUBLIC))


class TheViewsSectionTests(TestCase):

    def test_the_project_as_it_is_has_every_public_view_declared(self):
        report = section(run_check_security(), 1)

        self.assertNotIn('AVISO', report)
        self.assertIn('vistas publicas, todas justificadas', report)

    def test_a_new_undeclared_public_view_is_reported(self):
        rows = Command()._own_views()
        rows.append({
            'path': 'nueva/', 'name': 'nueva', 'namespace': 'core',
            'guarded': False, 'is_class': True,
            'callback': mock.Mock(), 'view_class': None,
        })

        with mock.patch.object(Command, '_own_views', return_value=rows):
            report = section(run_check_security(), 1)

        self.assertIn('core:nueva (/nueva/)', report)

    def test_a_guarded_view_is_not_reported(self):
        rows = [{
            'path': 'privada/', 'name': 'privada', 'namespace': 'core',
            'guarded': True, 'is_class': True,
            'callback': mock.Mock(), 'view_class': None,
        }]

        with mock.patch.object(Command, '_own_views', return_value=rows):
            report = section(run_check_security(), 1)

        self.assertNotIn('AVISO', report)

    def test_an_api_view_with_allow_any_counts_as_public(self):
        """La API nacio abierta por defecto; `AllowAny` explicito es publico."""
        rows = {row['name']: row for row in Command()._own_views()}

        self.assertFalse(rows['api-contact-create']['guarded'])
        self.assertTrue(rows['api-clients-lookup']['guarded'])
        self.assertTrue(rows['wizard']['guarded'])

    def test_the_admin_is_not_audited_route_by_route(self):
        paths = [row['path'] for row in Command()._own_views()]

        self.assertFalse(any(path.startswith('pa/admin/') for path in paths))


class TheThrottleSectionTests(TestCase):

    def test_the_forms_that_do_limit_are_recognised(self):
        report = section(run_check_security(), 2)

        for label in ('account:login', 'account:forgot_password',
                      'case_manager:public_query'):
            self.assertIn(f'OK    {label} limita', report)

    def test_a_form_without_a_brake_is_reported(self):
        report = section(run_check_security(), 2)

        # Estos cuatro son hallazgos reales de pag (ver docs/SEGURIDAD.md): el
        # comando los tiene que ver mientras no lleven freno.
        for label in ('account:register', 'api-contact-create',
                      'api-pqrs-create', 'core:index'):
            with self.subTest(label=label):
                self.assertRegex(
                    report, rf'(AVISO|OK)\s+{label}')

    def test_a_form_that_disappears_from_the_urls_is_reported(self):
        with mock.patch.object(check_security, 'THROTTLED_FORMS',
                               {'core:no-existe'}):
            report = section(run_check_security(), 2)

        self.assertIn('core:no-existe ya no existe', report)

    def test_a_module_level_rate_limit_named_in_the_view_counts(self):
        """
        `reset_by_ip = RateLimit(...)` a nivel de modulo: la vista lo nombra
        y eso basta; que otra vista del mismo modulo lo tenga no.
        """
        rows = {row['name']: row for row in Command()._own_views()}
        forgot = Command()._source_of(rows['forgot_password'])
        register = Command()._source_of(rows['register'])

        self.assertTrue(any(
            marker in forgot for marker in check_security.THROTTLE_MARKERS))
        self.assertFalse(any(
            marker in register for marker in check_security.THROTTLE_MARKERS))


class TheSettingsSectionTests(TestCase):

    def settings_report(self, **overrides):
        with override_settings(**overrides):
            return section(run_check_security(), 6)

    def test_a_short_server_key_is_reported(self):
        self.assertIn('SERVER_KEY tiene menos de 32',
                      self.settings_report(SERVER_KEY='corta'))

    def test_a_long_server_key_passes(self):
        self.assertIn('OK    SERVER_KEY',
                      self.settings_report(SERVER_KEY='k' * 40))

    def test_debug_on_is_reported(self):
        self.assertIn('DEBUG esta activado', self.settings_report(DEBUG=True))

    def test_production_needs_secure_cookies_and_https(self):
        report = self.settings_report(
            DEBUG=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False,
            SECURE_SSL_REDIRECT=False)

        for name in ('SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE',
                     'SECURE_SSL_REDIRECT'):
            self.assertIn(f'AVISO {name}', report)

    def test_a_cors_wildcard_is_reported(self):
        for override in (
            {'CORS_ALLOW_ALL_ORIGINS': True},
            {'CORS_ALLOWED_ORIGIN_REGEXES': [r'^https://.*\.example\.com$']},
            {'CORS_ALLOWED_ORIGINS': ['https://*.example.com']},
        ):
            with self.subTest(override=override):
                self.assertIn('CORS deja de estar enumerado',
                              self.settings_report(**override))

    def test_a_wildcard_host_is_reported(self):
        self.assertIn('ALLOWED_HOSTS contiene',
                      self.settings_report(ALLOWED_HOSTS=['*']))

    def test_the_default_admin_path_is_reported_in_production(self):
        self.assertIn('DJANGO_ADMIN_URL es la de por defecto',
                      self.settings_report(DEBUG=False, ADMIN_URL='admin/'))

    def test_the_local_memory_cache_is_reported(self):
        report = self.settings_report(CACHES={'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})

        self.assertIn('La cache no es compartida', report)

    def test_a_shared_cache_is_not(self):
        report = self.settings_report(CACHES={'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table'}})

        self.assertIn('Cache compartida', report)
        self.assertNotIn('La cache no es compartida', report)

    def test_a_missing_field_encryption_key_is_reported(self):
        self.assertIn('FIELD_ENCRYPTION_KEY sin configurar',
                      self.settings_report(FIELD_ENCRYPTION_KEY=''))


class TheReportTests(TestCase):

    def test_what_could_not_be_looked_at_is_said_apart(self):
        """No haber ejecutado bandit no es un hallazgo, pero tampoco se calla."""
        report = run_check_security()

        if 'SIN MIRAR' in report:
            self.assertRegex(report, r'\d comprobacion\(es\) no se han hecho')

    def test_strict_exits_with_a_code_when_there_are_findings(self):
        with mock.patch.object(Command, '_check_settings',
                               lambda self: self._finding('inventado')):
            report = run_check_security(strict=True)

        self.assertIn('[exit 1]', report)

    def test_without_strict_it_never_exits_with_a_code(self):
        with mock.patch.object(Command, '_check_settings',
                               lambda self: self._finding('inventado')):
            report = run_check_security()

        self.assertNotIn('[exit', report)
        self.assertIn('hallazgo(s)', report)

    def test_no_findings_says_so(self):
        patches = [mock.patch.object(Command, name, lambda self: None)
                   for name in (
                       '_check_unguarded_views', '_check_throttles',
                       '_check_shell_calls', '_check_string_sql',
                       '_check_uploads_are_not_served', '_check_settings',
                       '_check_bandit', '_check_dependencies',
                       '_check_dependencies_deeply')]

        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

        self.assertIn('Sin hallazgos', run_check_security())

    def test_shell_and_sql_patterns_match_what_they_should(self):
        for line in ('os.system("ls")', 'subprocess.run(x, shell=True)',
                     'os.popen("ls")'):
            self.assertTrue(check_security.SHELL_CALLS.search(line), line)

        self.assertTrue(check_security.STRING_SQL.search(
            'cursor.execute("SELECT %s" % x)'))
        self.assertTrue(check_security.STRING_SQL.search(
            'Modelo.objects.raw(f"SELECT {x}")'))
        self.assertFalse(check_security.STRING_SQL.search(
            'cursor.execute("SELECT 1")'))


class TheHealthCheckViewTests(TestCase):

    def test_it_answers_ok_with_the_three_checks(self):
        response = self.client.get('/health/')
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['response'], 'OK')
        self.assertEqual(set(data['checks']), {'database', 'cache', 'email'})

    def test_it_is_503_when_a_check_fails(self):
        from apps.common.core.views import HealthCheckView

        with mock.patch.object(
                HealthCheckView, '_check_cache',
                return_value={'ok': False, 'detail': 'Cache error: X'}):
            response = self.client.get('/health/')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['response'], 'Error')

    def test_it_never_leaks_the_message_of_an_error(self):
        """El nombre de la excepcion si; el mensaje puede llevar hosts."""
        from django.db import DatabaseError

        from apps.common.core.views import HealthCheckView

        # Se sustituye el `connection` del modulo de la vista, no el de Django:
        # el resto de la peticion (middleware, auditoria) sigue usando la base
        # de datos de verdad.
        broken = mock.Mock()
        broken.ensure_connection.side_effect = DatabaseError(
            'host secreto-db.interno:5432')

        with mock.patch('apps.common.core.views.connection', broken):
            response = self.client.get('/health/')

        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secreto-db', response.content.decode())
        self.assertIn('DatabaseError', response.content.decode())

    def test_an_unhandled_error_is_500_without_details(self):
        from apps.common.core.views import HealthCheckView

        with mock.patch.object(HealthCheckView, '_check_database',
                               side_effect=RuntimeError('interno')):
            response = self.client.get('/health/')

        self.assertEqual(response.status_code, 500)
        self.assertNotIn('interno', response.content.decode())


class TheHealthCommandTests(TestCase):

    def run_health(self, **options):
        out, err = StringIO(), StringIO()

        try:
            call_command('check_health', stdout=out, stderr=err, **options)
        except SystemExit as stop:
            out.write(f'\n[exit {stop.code}]')

        return out.getvalue() + err.getvalue()

    def test_in_process_everything_responds(self):
        report = self.run_health()

        self.assertIn('Todo responde', report)
        self.assertIn('Sesiones:', report)
        self.assertIn('guarda y relee', report)
        self.assertIn('Motor:', report)

    def test_in_process_a_failing_check_exits_with_a_code(self):
        from apps.common.core.views import HealthCheckView

        with mock.patch.object(
                HealthCheckView, '_check_email',
                return_value={'ok': False, 'detail': 'Email error'}):
            report = self.run_health()

        self.assertIn('No pasan: email', report)
        self.assertIn('[exit 1]', report)

    def fake_response(self, status, body):
        response = mock.MagicMock()
        response.status = status
        response.read.return_value = body.encode()
        response.__enter__.return_value = response

        return response

    @override_settings(PUBLIC_BASE_URL='https://sitio.example')
    def test_http_asks_the_public_url(self):
        body = json.dumps({'response': 'OK', 'checks': {
            'database': {'ok': True, 'detail': 'Database OK'}}})

        with mock.patch.object(
                check_health.urllib.request, 'urlopen',
                return_value=self.fake_response(200, body)) as opened:
            report = self.run_health(http=True)

        self.assertEqual(
            opened.call_args.args[0], 'https://sitio.example/health/')
        self.assertIn('Todo responde', report)

    @override_settings(PUBLIC_BASE_URL='file:///etc')
    def test_http_refuses_a_url_that_is_not_http(self):
        """`urlopen` abre tambien `file://`; la URL sale de la configuracion."""
        with mock.patch.object(check_health.urllib.request, 'urlopen') as opened:
            report = self.run_health(http=True)

        opened.assert_not_called()
        self.assertIn('[exit 1]', report)

    @override_settings(PUBLIC_BASE_URL='https://sitio.example')
    def test_http_unreachable_says_the_problem_is_in_front(self):
        with mock.patch.object(
                check_health.urllib.request, 'urlopen',
                side_effect=urllib.error.URLError('sin ruta')):
            report = self.run_health(http=True)

        self.assertIn('delante de la aplicacion', report)
        self.assertIn('[exit 1]', report)

    @override_settings(PUBLIC_BASE_URL='https://sitio.example')
    def test_http_not_json_is_reported(self):
        with mock.patch.object(
                check_health.urllib.request, 'urlopen',
                return_value=self.fake_response(200, '<html>')):
            report = self.run_health(http=True)

        self.assertIn('no es JSON', report)
        self.assertIn('[exit 1]', report)

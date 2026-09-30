# apps/common/utils/tests/test_middleware.py
"""
La capa inicial de middlewares, de punta a punta.

Lo que mas importa fijar es lo que NO debe bloquear: el proxy de Next
(fundacionattlas.org, desde servidores de Vercel) comparte una unica IP de
salida entre todos los visitantes, y bloquearla dejaria fuera al sitio entero.
Con `X-Server-Key` valida la IP efectiva es la de `X-Client-IP`.

    manage.py test apps.common.utils.tests.test_middleware
"""

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .. import scanning
from ..middleware import RedirectAuthenticatedUserMiddleware
from ..models import IPBlockedModel, WhiteListedIPModel

KEY = 'k' * 40
PROXY_IP = '76.76.21.21'
VISITOR = '203.0.113.50'
OTHER_VISITOR = '203.0.113.51'
SCANNER = '198.51.100.7'
BROWSER = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/120 Safari/537.36')


class ExportsTests(SimpleTestCase):
    def test_the_dotted_paths_of_settings_still_resolve(self):
        from django.conf import settings
        from django.utils.module_loading import import_string

        for path in settings.MIDDLEWARE:
            if path.startswith('apps.common.utils.middleware.'):
                import_string(path)

    def test_the_final_order(self):
        from django.conf import settings

        order = list(settings.MIDDLEWARE)
        prefix = 'apps.common.utils.middleware.'

        self.assertLess(
            order.index(prefix + 'RedirectWWWMiddleware'),
            order.index('django.contrib.sessions.middleware.SessionMiddleware'),
        )
        for name in ('RedirectAuthenticatedUserMiddleware',
                     'BlockBadBotsMiddleware',
                     'DetectSuspiciousRequestMiddleware'):
            self.assertGreater(
                order.index(prefix + name),
                order.index(
                    'django.contrib.auth.middleware.AuthenticationMiddleware'),
            )
        self.assertEqual(order[-1], 'axes.middleware.AxesMiddleware')


@override_settings(ATTLAS_SERVER_KEY=KEY, USE_X_FORWARDED_FOR=False)
class ScannerAndBrowserTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def get(self, path='/', agent=BROWSER, ip=SCANNER, **extra):
        return self.client.get(
            path, REMOTE_ADDR=ip, HTTP_USER_AGENT=agent, **extra)

    def test_known_scanner_agents_are_blocked(self):
        for agent in ('sqlmap/1.8#stable', 'Nikto/2.5.0'):
            with self.subTest(agent=agent):
                response = self.get(agent=agent)

                self.assertEqual(response.status_code, 404)

        self.assertTrue(IPBlockedModel.objects.filter(
            current_ip=SCANNER).exists())

    def test_a_scanner_stays_blocked_with_a_browser_agent(self):
        self.get(agent='sqlmap/1.8')

        response = self.get('/nosotros/', agent=BROWSER)

        self.assertEqual(response.status_code, 404)

    def test_a_normal_browser_passes(self):
        self.assertEqual(self.get('/').status_code, 200)
        self.assertFalse(IPBlockedModel.objects.exists())

    def test_the_proxy_with_axios_or_node_agent_passes(self):
        for agent in ('axios/1.7.2', 'node', 'node-fetch/1.0',
                      'Next.js Middleware', 'undici'):
            with self.subTest(agent=agent):
                response = self.get(
                    '/', agent=agent, ip=PROXY_IP,
                    HTTP_X_SERVER_KEY=KEY, HTTP_X_CLIENT_IP=VISITOR)

                self.assertEqual(response.status_code, 200)

        self.assertFalse(IPBlockedModel.objects.exists())

    def test_a_404_burst_through_the_proxy_blocks_the_visitor_not_the_proxy(self):
        headers = {'HTTP_X_SERVER_KEY': KEY, 'HTTP_X_CLIENT_IP': VISITOR}

        for index in range(scanning.threshold() + 15):
            self.get(f'/no-existe-{index}/', agent='axios/1.7.2',
                     ip=PROXY_IP, **headers)

        self.assertTrue(IPBlockedModel.objects.filter(
            current_ip=VISITOR).exists())
        self.assertFalse(IPBlockedModel.objects.filter(
            current_ip=PROXY_IP).exists())

        # Otro visitante que sale por la misma IP del proxy sigue entrando.
        other = self.get('/', agent='axios/1.7.2', ip=PROXY_IP,
                         HTTP_X_SERVER_KEY=KEY,
                         HTTP_X_CLIENT_IP=OTHER_VISITOR)

        self.assertEqual(other.status_code, 200)

    def test_a_forged_client_ip_without_key_blocks_only_the_real_caller(self):
        for index in range(scanning.threshold() + 15):
            self.get(f'/no-existe-{index}/', ip=SCANNER,
                     HTTP_X_CLIENT_IP=VISITOR)

        self.assertTrue(IPBlockedModel.objects.filter(
            current_ip=SCANNER).exists())
        self.assertFalse(IPBlockedModel.objects.filter(
            current_ip=VISITOR).exists())


class NotFoundBurstTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_distinct_404s_block(self):
        for index in range(scanning.threshold() + 15):
            self.client.get(f'/inexistente-{index}/', REMOTE_ADDR=SCANNER)

        entry = IPBlockedModel.objects.get(current_ip=SCANNER)

        self.assertGreater(entry.blocked_until, timezone.now())

    def test_reloading_the_same_404_twenty_times_does_not_block(self):
        for _ in range(20):
            response = self.client.get('/enlace-roto/', REMOTE_ADDR=SCANNER)

            self.assertEqual(response.status_code, 404)

        self.assertFalse(IPBlockedModel.objects.exists())

    def test_it_fails_open_when_the_cache_is_down(self):
        with mock.patch.object(cache, 'get', side_effect=RuntimeError), \
                mock.patch.object(cache, 'set', side_effect=RuntimeError):
            for index in range(scanning.threshold() + 15):
                response = self.client.get(
                    f'/inexistente-{index}/', REMOTE_ADDR=SCANNER)

                self.assertEqual(response.status_code, 404)

        self.assertFalse(IPBlockedModel.objects.exists())


class BlockedRequestTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def block(self, ip=SCANNER, until=timedelta(minutes=30)):
        return IPBlockedModel.objects.create(
            current_ip=ip,
            reason=IPBlockedModel.ReasonsChoices.SERVER_HTTP_REQUEST,
            blocked_until=timezone.now() + until,
            session_info={'attempt_count': 3, 'paths': []},
        )

    def test_a_blocked_ip_gets_a_bare_404(self):
        self.block()

        response = self.client.get('/contacto/', REMOTE_ADDR=SCANNER)
        body = response.content.decode().lower()

        self.assertEqual(response.status_code, 404)
        for leak in ('blocked', 'suspicious', 'attempt'):
            self.assertNotIn(leak, body)

    def test_the_attempt_is_counted(self):
        entry = self.block()

        self.client.get('/contacto/', REMOTE_ADDR=SCANNER)
        entry.refresh_from_db()

        self.assertEqual(entry.session_info['attempt_count'], 4)

    def test_whitelisting_unblocks(self):
        self.block()
        WhiteListedIPModel.objects.create(current_ip=SCANNER)

        self.assertEqual(
            self.client.get('/', REMOTE_ADDR=SCANNER).status_code, 200)

    def test_an_expired_block_lets_through(self):
        self.block(until=timedelta(minutes=-1))

        self.assertEqual(
            self.client.get('/', REMOTE_ADDR=SCANNER).status_code, 200)

    def test_staff_is_never_blocked(self):
        user = get_user_model().objects.create_user(
            username='staff', email='staff@example.com',
            password='pw-tests-123', is_staff=True)
        self.block()
        self.client.force_login(user)

        response = self.client.get('/', REMOTE_ADDR=SCANNER)

        self.assertEqual(response.status_code, 200)

    @override_settings(ATTLAS_SERVER_KEY=KEY)
    def test_the_proxy_ip_is_not_blocked_when_a_visitor_is(self):
        self.block(ip=VISITOR)

        visitor = self.client.get(
            '/', REMOTE_ADDR=PROXY_IP,
            HTTP_X_SERVER_KEY=KEY, HTTP_X_CLIENT_IP=VISITOR)
        other = self.client.get(
            '/', REMOTE_ADDR=PROXY_IP,
            HTTP_X_SERVER_KEY=KEY, HTTP_X_CLIENT_IP=OTHER_VISITOR)

        self.assertEqual(visitor.status_code, 404)
        self.assertEqual(other.status_code, 200)


class RedirectAuthenticatedUserTests(TestCase):
    def test_an_authenticated_user_leaves_the_login_and_register(self):
        user = get_user_model().objects.create_user(
            username='u', email='u@example.com', password='pw-tests-123')
        self.client.force_login(user)

        for name in ('account:login', 'account:register'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))

                self.assertEqual(response.status_code, 302)
                self.assertEqual(response['Location'], reverse('core:index'))

    def test_an_anonymous_visitor_sees_the_login(self):
        self.assertEqual(
            self.client.get(reverse('account:login')).status_code, 200)

    def test_it_lets_through_when_there_is_no_user(self):
        middleware = RedirectAuthenticatedUserMiddleware(lambda request: 'ok')

        self.assertEqual(middleware(RequestFactory().get('/')), 'ok')

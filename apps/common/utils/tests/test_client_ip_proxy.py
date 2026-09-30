from types import SimpleNamespace

from axes.models import AccessAttempt
from axes.utils import reset
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from rest_framework.request import Request
from rest_framework.test import APITestCase

from apps.common.utils.api_keys import server_key_is_valid
from apps.common.utils.client_ip import get_client_ip


@override_settings(ATTLAS_SERVER_KEY='x' * 40, USE_X_FORWARDED_FOR=False)
class ClientIPProxyTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, **headers):
        return self.factory.get('/', REMOTE_ADDR='192.0.2.1', **headers)

    def test_valid_key_trusts_client_ip(self):
        request = self.request(HTTP_X_SERVER_KEY='x' * 40,
                               HTTP_X_CLIENT_IP='203.0.113.7')
        self.assertEqual(get_client_ip(request), '203.0.113.7')
        self.assertEqual(get_client_ip(Request(request)), '203.0.113.7')

    def test_missing_or_wrong_key_ignores_client_ip(self):
        for key in ('', 'wrong'):
            with self.subTest(key=key):
                self.assertEqual(get_client_ip(self.request(
                    HTTP_X_SERVER_KEY=key, HTTP_X_CLIENT_IP='203.0.113.7',
                )), '192.0.2.1')

    def test_invalid_or_missing_client_ip_falls_back(self):
        for ip in ('abc', '', '   ', None):
            with self.subTest(ip=ip):
                headers = {'HTTP_X_SERVER_KEY': 'x' * 40}
                if ip is not None:
                    headers['HTTP_X_CLIENT_IP'] = ip
                self.assertEqual(get_client_ip(self.request(**headers)), '192.0.2.1')

    def test_first_ip_and_normalized_ipv6(self):
        for value, expected in (
            (' 203.0.113.7, 10.0.0.1', '203.0.113.7'),
            (' 2001:0DB8:0000::1 ', '2001:db8::1'),
        ):
            with self.subTest(value=value):
                self.assertEqual(get_client_ip(self.request(
                    HTTP_X_SERVER_KEY='x' * 40, HTTP_X_CLIENT_IP=value,
                )), expected)

    @override_settings(ATTLAS_SERVER_KEY='')
    def test_empty_configured_key_never_trusts_header(self):
        for key in ('', 'x' * 40):
            self.assertEqual(get_client_ip(self.request(
                HTTP_X_SERVER_KEY=key, HTTP_X_CLIENT_IP='203.0.113.7',
            )), '192.0.2.1')

    @override_settings(USE_X_FORWARDED_FOR=True)
    def test_forwarded_fallback_and_client_ip_precedence(self):
        for ip, expected in (('abc', '198.51.100.1'),
                             ('203.0.113.7', '203.0.113.7')):
            self.assertEqual(get_client_ip(self.request(
                HTTP_X_SERVER_KEY='x' * 40, HTTP_X_CLIENT_IP=ip,
                HTTP_X_FORWARDED_FOR='198.51.100.1, 10.0.0.1',
            )), expected)

    def test_server_key_supports_meta_only_and_headers_only(self):
        for request in (
            SimpleNamespace(META={'HTTP_X_SERVER_KEY': 'x' * 40}),
            SimpleNamespace(headers={'X-Server-Key': 'x' * 40}),
        ):
            self.assertTrue(server_key_is_valid(request))

    def test_helpers_do_not_raise_for_malformed_requests(self):
        self.assertFalse(server_key_is_valid(None))
        self.assertFalse(server_key_is_valid(SimpleNamespace(headers={'X-Server-Key': 42})))
        self.assertEqual(get_client_ip(None), '')
        self.assertEqual(get_client_ip(SimpleNamespace(META=42)), '')


@override_settings(ATTLAS_SERVER_KEY='x' * 40, SECURE_SSL_REDIRECT=False,
                   AXES_ENABLED=True, USE_X_FORWARDED_FOR=False)
class ClientIPProxyLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        reset()
        self.addCleanup(cache.clear)
        self.addCleanup(reset)
        self.url = reverse('api-insolvency-login')
        self.client.credentials(HTTP_X_SERVER_KEY='x' * 40)

    def login(self, ip):
        return self.client.post(self.url, {
            'document_number': 'missing', 'birth_date': '1990-01-02',
            'user': 'same-consultant', 'password': 'wrong',
        }, format='json', REMOTE_ADDR='192.0.2.1', HTTP_X_CLIENT_IP=ip)

    @override_settings(AXES_FAILURE_LIMIT=100)
    def test_login_ip_quotas_are_independent(self):
        for _ in range(10):
            self.assertEqual(self.login('203.0.113.7').status_code, 400)
        self.assertEqual(self.login('203.0.113.7').status_code, 429)
        self.assertEqual(self.login('203.0.113.8').status_code, 400)

    @override_settings(AXES_FAILURE_LIMIT=3)
    def test_axes_lockout_is_per_client_ip_and_username(self):
        for _ in range(3):
            self.assertEqual(self.login('203.0.113.7').status_code, 400)
        self.assertTrue(AccessAttempt.objects.filter(
            ip_address='203.0.113.7', username='same-consultant',
            failures_since_start=3,
        ).exists())
        self.assertEqual(self.login('203.0.113.7').status_code, 429)
        self.assertEqual(self.login('203.0.113.8').status_code, 400)

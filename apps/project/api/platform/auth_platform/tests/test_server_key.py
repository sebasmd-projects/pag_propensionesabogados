from uuid import UUID
from django.core import checks
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, resolve, reverse
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory, APITestCase
from apps.common.utils.api_keys import HasServerKey
from apps.common.utils.checks import check_attlas_server_key
from apps.project.api.platform.calculator.api.views import ClientViewSet

SERVER_KEY = 'x' * 40
OBJECT_ID = UUID('00000000-0000-0000-0000-000000000001')
ROUTES = [
    ('api-insolvency-login', {}, ('post',)),
    ('api-insolvency-register', {}, ('post',)),
    ('api-clients-lookup', {}, ('post',)),
    ('api-clients-lookup-verify', {}, ('post',)),
    ('api-insolvency-consultants-register', {}, ('post',)),
    ('token-info', {}, ('get',)),
    ('calculator_api:client-list', {}, ('post',)),
    ('calculator_api:client-detail', {'pk': OBJECT_ID}, ('get', 'put', 'patch')),
    ('insolvency_form_api:wizard', {'id': OBJECT_ID}, ('get', 'put', 'patch')),
    ('insolvency_form_api:wizard-me', {}, ('get', 'put', 'patch')),
    ('insolvency_form_api:signature-update', {'id': OBJECT_ID}, ('get', 'put', 'patch')),
    ('insolvency_form_api:signature-create', {}, ('post',)),
]


@override_settings(ATTLAS_SERVER_KEY=SERVER_KEY, SECURE_SSL_REDIRECT=False)
class ServerKeyAPITests(APITestCase):
    def setUp(self):
        cache.clear()

    def assert_routes_denied(self, headers):
        for name, kwargs, methods in ROUTES:
            for method in methods:
                with self.subTest(route=name, method=method):
                    response = getattr(self.client, method)(reverse(name, kwargs=kwargs), **headers)
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(str(response.data['detail']), HasServerKey.message)

    def test_all_routes_without_header_are_forbidden(self):
        self.assert_routes_denied({})

    def test_all_routes_with_wrong_key_are_forbidden(self):
        self.assert_routes_denied({'HTTP_X_SERVER_KEY': 'wrong'})

    @override_settings(ATTLAS_SERVER_KEY='')
    def test_empty_configuration_denies_all_routes(self):
        self.assert_routes_denied({'HTTP_X_SERVER_KEY': ''})

    def test_legacy_search_route_is_removed(self):
        with self.assertRaises(NoReverseMatch):
            reverse('api-calc-client-search')
        for headers in ({}, {'HTTP_X_SERVER_KEY': SERVER_KEY}):
            self.assertEqual(self.client.get('/api/v1/clients/search/', **headers).status_code, 404)

    def test_correct_key_preserves_login_validation(self):
        response = self.client.post(reverse('api-insolvency-login'), {}, HTTP_X_SERVER_KEY=SERVER_KEY)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {'document_number', 'birth_date', 'password', 'user'})

    def test_correct_key_does_not_replace_bearer_authentication(self):
        for name, kwargs, methods in ROUTES:
            if name.startswith('insolvency_form_api:'):
                with self.subTest(route=name):
                    url = reverse(name, kwargs=kwargs)
                    self.assertEqual(resolve(url).func.cls.permission_classes, [HasServerKey, IsAuthenticated])
                    for method in methods:
                        with self.subTest(method=method):
                            response = getattr(self.client, method)(url, HTTP_X_SERVER_KEY=SERVER_KEY)
                            self.assertEqual(response.status_code, 401)

    def test_duplicate_calculator_search_is_removed(self):
        self.assertFalse(hasattr(ClientViewSet, 'search'))
        with self.assertRaises(NoReverseMatch):
            reverse('calculator_api:client-search')


@override_settings(ATTLAS_SERVER_KEY=SERVER_KEY)
class HasServerKeyTests(TestCase):
    def test_matching_key_is_allowed(self):
        self.assertTrue(HasServerKey().has_permission(
            APIRequestFactory().get('/', HTTP_X_SERVER_KEY=SERVER_KEY), None))

    def test_missing_empty_wrong_and_unicode_keys_are_denied(self):
        for headers in ({}, {'HTTP_X_SERVER_KEY': ''}, {'HTTP_X_SERVER_KEY': 'wrong'}, {'HTTP_X_SERVER_KEY': '\u00f1' * 40}):
            with self.subTest(headers=headers), self.assertRaisesMessage(PermissionDenied, HasServerKey.message):
                HasServerKey().has_permission(APIRequestFactory().get('/', **headers), None)

    @override_settings(ATTLAS_SERVER_KEY='')
    def test_empty_configuration_never_allows(self):
        for key in ('', SERVER_KEY):
            with self.subTest(key=key), self.assertRaises(PermissionDenied):
                HasServerKey().has_permission(APIRequestFactory().get('/', HTTP_X_SERVER_KEY=key), None)

    @override_settings(ATTLAS_SERVER_KEY='\u00f1' * 40)
    def test_matching_unicode_key_uses_bytes(self):
        self.assertTrue(HasServerKey().has_permission(
            APIRequestFactory().get('/', HTTP_X_SERVER_KEY='\u00f1' * 40), None))


class ServerKeyCheckTests(TestCase):
    @override_settings(DEBUG=False)
    def test_production_rejects_empty_and_short_keys(self):
        for key in ('', 'x' * 31):
            with self.subTest(length=len(key)), override_settings(ATTLAS_SERVER_KEY=key):
                errors = check_attlas_server_key(None)
                self.assertEqual(len(errors), 1)
                self.assertIsInstance(errors[0], checks.Error)
                self.assertEqual(errors[0].id, 'utils.E001')

    @override_settings(DEBUG=False)
    def test_production_accepts_at_least_32_characters(self):
        for key in ('x' * 32, SERVER_KEY):
            with self.subTest(length=len(key)), override_settings(ATTLAS_SERVER_KEY=key):
                self.assertEqual(check_attlas_server_key(None), [])

    @override_settings(DEBUG=True, ATTLAS_SERVER_KEY='')
    def test_debug_warns_for_empty_key(self):
        warnings = check_attlas_server_key(None)
        self.assertEqual(len(warnings), 1)
        self.assertIsInstance(warnings[0], checks.Warning)
        self.assertEqual(warnings[0].id, 'utils.W001')

    @override_settings(DEBUG=False, ATTLAS_SERVER_KEY='')
    def test_check_is_registered(self):
        self.assertIn('utils.E001', [item.id for item in checks.run_checks(tags=[checks.Tags.security])])

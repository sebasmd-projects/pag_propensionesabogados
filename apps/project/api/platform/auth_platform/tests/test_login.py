from datetime import date
from unittest.mock import Mock, patch
from uuid import uuid4

from axes.utils import reset
from django.conf import settings
from django.contrib.auth.signals import user_login_failed
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.common.utils.functions import generate_token
from ..api import serializers as login_serializers
from ..models import AttlasInsolvencyAuthConsultantsModel, AttlasInsolvencyAuthModel


@override_settings(ATTLAS_SERVER_KEY='x' * 40, SECURE_SSL_REDIRECT=False,
                   AXES_ENABLED=True)
class AttlasLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        reset()
        self.addCleanup(cache.clear)
        self.customer = AttlasInsolvencyAuthModel.objects.create(
            document_number='123456789', birth_date=date(1990, 1, 2),
        )
        self.consultant = AttlasInsolvencyAuthConsultantsModel.objects.create(
            first_name='Ana', last_name='Perez', user='AP', password='known-password',
        )
        self.client.credentials(HTTP_X_SERVER_KEY='x' * 40)
        self.url = reverse('api-insolvency-login')
        self.payload = {
            'document_number': '123456789', 'birth_date': '1990-01-02',
            'user': ' ap ', 'password': 'known-password',
        }

    def login(self, **changes):
        return self.client.post(self.url, {**self.payload, **changes}, format='json')

    def test_success(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['token'])
        self.assertEqual(response.data['user'], 'AP')
        self.assertEqual(response.data['expires_in'], settings.ATTLAS_TOKEN_TIMEOUT)

    def test_failures_are_identical_and_each_emits_one_signal(self):
        receiver = Mock()
        user_login_failed.connect(receiver, weak=False)
        self.addCleanup(user_login_failed.disconnect, receiver)
        bodies = []
        for change in ({'document_number': 'missing'}, {'birth_date': '2000-01-01'},
                       {'user': ' missing '}, {'password': 'wrong'}):
            with self.subTest(change=change):
                receiver.reset_mock()
                response = self.login(**change)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(set(response.data), {'non_field_errors'})
                bodies.append(response.content)
                receiver.assert_called_once()
                self.assertEqual(receiver.call_args.kwargs['credentials'], {
                    'username': change.get('user', 'ap').strip().lower(),
                })
        self.assertTrue(all(body == bodies[0] for body in bodies))

    def test_invalid_credentials_are_translated(self):
        response = self.client.post(
            self.url, {**self.payload, 'password': 'wrong'}, format='json',
            HTTP_ACCEPT_LANGUAGE='es',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {
            'non_field_errors': ['Credenciales inválidas.'],
        })

    def test_missing_customer_still_checks_consultant_password(self):
        with patch.object(AttlasInsolvencyAuthConsultantsModel, 'check_password',
                          return_value=True) as check:
            self.assertEqual(self.login(document_number='missing').status_code, 400)
        check.assert_called_once_with('known-password')

    def test_missing_consultant_checks_dummy_hash_and_records_failure_once(self):
        with patch.object(login_serializers, 'check_password',
                          wraps=login_serializers.check_password) as check, \
             patch.object(login_serializers, 'note_failure') as failure:
            self.assertEqual(self.login(user=' missing ').status_code, 400)
        check.assert_called_once_with('known-password', login_serializers.DUMMY_HASH)
        failure.assert_called_once()
        self.assertEqual(failure.call_args.kwargs,
                         {'username': 'MISSING', 'reason': 'attlas_login'})

    @override_settings(AXES_FAILURE_LIMIT=3)
    def test_axes_blocks_correct_password_after_failure_limit(self):
        for _ in range(settings.AXES_FAILURE_LIMIT):
            self.assertEqual(self.login(password='wrong').status_code, 400)
        with patch.object(login_serializers.AttlasInsolvencyAuthSerializer,
                          'validate') as validate:
            response = self.login(user='AP')
        validate.assert_not_called()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data, {
            'detail': 'Demasiados intentos. Intente más tarde.',
        })

    def test_ip_quota_includes_successful_logins(self):
        for _ in range(10):
            self.assertEqual(self.login().status_code, 200)
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data, {
            'detail': 'Demasiados intentos. Intente más tarde.',
        })
        response = self.client.post(self.url, self.payload, format='json',
                                    REMOTE_ADDR='192.0.2.10')
        self.assertEqual(response.status_code, 200)

    def test_invalid_token_info_hides_internal_error(self):
        response = self.client.get(reverse('token-info'),
                                   HTTP_AUTHORIZATION='Bearer invalid')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {'detail': 'Token inválido o expirado.'})
        with patch('apps.project.api.platform.auth_platform.api.views.verify_token',
                   side_effect=ValueError('private internal exception')):
            response = self.client.get(reverse('token-info'),
                                       HTTP_AUTHORIZATION='Bearer invalid')
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(b'private internal exception', response.content)
        self.assertEqual(response.data, {'detail': 'Token inválido o expirado.'})

    def test_token_for_missing_customer_is_generic_401(self):
        response = self.client.get(reverse('token-info'),
            HTTP_AUTHORIZATION=f'Bearer {generate_token(str(uuid4()))}')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {'detail': 'Token inválido o expirado.'})

    def test_token_info_success(self):
        response = self.client.get(reverse('token-info'),
            HTTP_AUTHORIZATION=f'Bearer {generate_token(str(self.customer.pk))}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['document_number'], self.payload['document_number'])

    def test_missing_server_key_is_forbidden(self):
        self.client.credentials()
        self.assertEqual(self.login().status_code, 403)

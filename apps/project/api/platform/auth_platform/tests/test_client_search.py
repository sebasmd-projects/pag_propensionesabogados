from datetime import date
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.project.api.platform.auth_platform.models import AttlasInsolvencyAuthModel
from apps.project.api.platform.insolvency_form.models import AttlasInsolvencyFormModel


@override_settings(ATTLAS_SERVER_KEY='x' * 40, SECURE_SSL_REDIRECT=False)
class ClientSearchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AttlasInsolvencyAuthModel.objects.create(
            document_number='123456789', birth_date=date(1990, 1, 1),
        )
        cls.form = AttlasInsolvencyFormModel.objects.create(
            user=cls.user, debtor_first_name='Nombre privado',
            debtor_last_name='Apellido privado', debtor_email='privado@example.com',
            debtor_cell_phone='3001234567', debtor_address='Calle privada 123',
        )

    def setUp(self):
        cache.clear()
        self.url = reverse('api-calc-client-search')
        self.client.credentials(HTTP_X_SERVER_KEY='x' * 40)

    def search(self, document='123456789', **headers):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url, {
                'documentNumber': document, 'birthDate': '1990-01-01',
            }, **headers)
        for query in queries:
            self.assertNotIn(AttlasInsolvencyAuthModel._meta.db_table, query['sql'])
            self.assertNotIn(AttlasInsolvencyFormModel._meta.db_table, query['sql'])
        return response

    def test_existing_client_returns_no_personal_data(self):
        response = self.search()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'No encontrado'})
        for value in (
            'firstName', 'lastName', 'email', 'phone', 'address', 'form_id', 'id',
            self.form.debtor_first_name, self.form.debtor_last_name,
            self.form.debtor_email, self.form.debtor_cell_phone,
            self.form.debtor_address, str(self.form.id), str(self.user.id),
        ):
            with self.subTest(value=value):
                self.assertNotIn(value, response.content.decode())

    def test_missing_client_returns_identical_response(self):
        existing = self.search()
        missing = self.search('999999999')
        self.assertEqual(missing.status_code, existing.status_code)
        self.assertEqual(missing.content, existing.content)

    def test_invalid_parameters_return_400(self):
        for params in ({}, {'documentNumber': '', 'birthDate': '1990-01-01'},
                       {'documentNumber': '123456789', 'birthDate': 'invalid'}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url, params).status_code, 400)

    def test_document_and_ip_limits(self):
        for _ in range(5):
            self.assertEqual(self.search().status_code, 404)
        response = self.search(' 123456789 ')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {
            'detail': 'Demasiadas solicitudes. Intente más tarde.',
        })
        for attempt in range(7, 21):
            self.assertEqual(self.search(str(attempt)).status_code, 404)
        self.assertEqual(self.search('21').status_code, 429)
        # El rechazo por IP también consume el cupo del documento.
        for _ in range(4):
            self.assertEqual(self.search('21', REMOTE_ADDR='192.0.2.1').status_code, 404)
        self.assertEqual(self.search('21', REMOTE_ADDR='192.0.2.1').status_code, 429)

    def test_document_limit_is_shared_across_ips(self):
        for attempt in range(5):
            self.assertEqual(self.search(REMOTE_ADDR=f'192.0.2.{attempt + 1}').status_code, 404)
        self.assertEqual(self.search(REMOTE_ADDR='192.0.2.6').status_code, 429)

    @patch('apps.common.utils.throttling.cache.incr', return_value=None)
    def test_broken_cache_fails_closed(self, incr):
        response = self.search()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {
            'detail': 'Demasiadas solicitudes. Intente más tarde.',
        })
        self.assertEqual(incr.call_count, 2)

    def test_missing_server_key_is_forbidden(self):
        self.client.credentials()
        self.assertEqual(self.search().status_code, 403)

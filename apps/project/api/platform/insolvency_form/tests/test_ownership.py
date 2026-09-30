from datetime import date

from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.common.utils.functions.token_utils import generate_token
from apps.project.api.platform.auth_platform.models import AttlasInsolvencyAuthModel
from apps.project.api.platform.insolvency_form.models import (
    AttlasInsolvencyFormModel,
    AttlasInsolvencySignatureModel,
)


@override_settings(SERVER_KEY='x' * 40, SECURE_SSL_REDIRECT=False)
class OwnershipTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a = AttlasInsolvencyAuthModel.objects.create(
            document_number='10001', birth_date=date(1990, 1, 1))
        cls.user_b = AttlasInsolvencyAuthModel.objects.create(
            document_number='10002', birth_date=date(1991, 1, 1))
        cls.form_a = AttlasInsolvencyFormModel.objects.create(user=cls.user_a)
        cls.form_b = AttlasInsolvencyFormModel.objects.create(user=cls.user_b)

    def setUp(self):
        self.headers = {
            'HTTP_X_SERVER_KEY': 'x' * 40,
            'HTTP_AUTHORIZATION': 'Bearer ' + generate_token(str(self.user_a.id)),
        }

    def url(self, name, form=None):
        namespace = 'calculator_api' if name.startswith('client-') else 'insolvency_form_api'
        kwargs = None if form is None else {
            'pk' if name.startswith('client-') else 'id': form.id}
        return reverse(f'{namespace}:{name}', kwargs=kwargs)

    def test_wizard_own_form_and_me(self):
        for url in (self.url('wizard', self.form_a), self.url('wizard-me')):
            with self.subTest(url=url):
                response = self.client.get(url, **self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(str(response.data['id']), str(self.form_a.id))
                self.assertEqual(str(response.data['user']), str(self.user_a.id))

    def test_wizard_foreign_form_is_not_found(self):
        for method in ('get', 'patch', 'put'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.url('wizard', self.form_b),
                    {'accept_terms_and_conditions': True}, **self.headers)
                self.assertEqual(response.status_code, 404)
        self.form_b.refresh_from_db()
        self.assertEqual(self.form_b.user_id, self.user_b.id)
        self.assertFalse(self.form_b.accept_terms_and_conditions)

    def test_wizard_me_creates_own_missing_form(self):
        self.form_a.delete()
        response = self.client.get(self.url('wizard-me'), **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data['user']), str(self.user_a.id))
        self.assertTrue(AttlasInsolvencyFormModel.objects.filter(user=self.user_a).exists())

    def test_wizard_own_patch(self):
        response = self.client.patch(self.url('wizard', self.form_a),
            {'accept_terms_and_conditions': True}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.form_a.refresh_from_db()
        self.assertTrue(self.form_a.accept_terms_and_conditions)

    def test_signature_update_foreign_form_does_not_create_signature(self):
        for method in ('get', 'patch', 'put'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.url('signature-update', self.form_b),
                    {'signature': 'forged'}, **self.headers)
                self.assertEqual(response.status_code, 404)
        self.assertFalse(AttlasInsolvencySignatureModel.objects.filter(form=self.form_b).exists())

    def test_signature_update_own_form(self):
        url = self.url('signature-update', self.form_a)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'signed': True})
        response = self.client.patch(url, {'signature': 'updated'}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'signed': True})
        self.assertEqual(AttlasInsolvencySignatureModel.objects.get(form=self.form_a).signature, 'updated')

    def test_wizard_signature_step_still_uses_form(self):
        self.form_a.current_step = 11
        self.form_a.save()
        url = self.url('wizard', self.form_a) + '?step=11'
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['signed'])
        response = self.client.patch(url, {'signature': 'wizard-signature'}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['signed'])
        self.assertEqual(
            AttlasInsolvencySignatureModel.objects.get(form=self.form_a).signature,
            'wizard-signature',
        )

    def test_signature_create_and_update_use_authenticated_user(self):
        other = AttlasInsolvencySignatureModel.objects.create(form=self.form_b, signature='original')
        for payload in ({'signature': 'first'},
                        {'signature': 'second', 'cedula': self.user_b.document_number}):
            with self.subTest(payload=payload):
                response = self.client.post(self.url('signature-create'), payload, **self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, {'signed': True})
                self.assertEqual(AttlasInsolvencySignatureModel.objects.get(form=self.form_a).signature, payload['signature'])
                other.refresh_from_db()
                self.assertEqual(other.signature, 'original')
        self.assertEqual(AttlasInsolvencySignatureModel.objects.count(), 2)

    def test_client_foreign_form_is_not_found(self):
        for method in ('get', 'patch', 'put'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.url('client-detail', self.form_b),
                    {'firstName': 'forged'}, **self.headers)
                self.assertEqual(response.status_code, 404)
        self.form_b.refresh_from_db()
        self.assertNotEqual(self.form_b.debtor_first_name, 'forged')

    def test_client_own_form_read_and_update(self):
        url = self.url('client-detail', self.form_a)
        self.assertEqual(self.client.get(url, **self.headers).status_code, 200)
        for method in ('patch', 'put'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, {'firstName': method}, **self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['firstName'], method)
                self.form_a.refresh_from_db()
                self.assertEqual(self.form_a.debtor_first_name, method)

    def test_client_registration_remains_public_with_server_key(self):
        response = self.client.post(self.url('client-list'), {
            'documentNumber': '10003', 'birthDate': '1992-01-01',
            'firstName': 'Nuevo', 'lastName': 'Cliente',
        }, HTTP_X_SERVER_KEY='x' * 40)
        self.assertEqual(response.status_code, 201)
        user = AttlasInsolvencyAuthModel.objects.get(insolvency_form__debtor_first_name='Nuevo')
        self.assertEqual(user.document_number, '10003')
        self.assertTrue(AttlasInsolvencyFormModel.objects.filter(user=user).exists())

    def protected_routes(self):
        return [
            ('wizard', self.form_a, ('get', 'patch', 'put')),
            ('wizard-me', None, ('get', 'patch', 'put')),
            ('signature-update', self.form_a, ('get', 'patch', 'put')),
            ('signature-create', None, ('post',)),
            ('client-detail', self.form_a, ('get', 'patch', 'put')),
        ]

    def test_protected_routes_require_token(self):
        for name, form, methods in self.protected_routes():
            for method in methods:
                with self.subTest(route=name, method=method):
                    response = getattr(self.client, method)(self.url(name, form),
                        HTTP_X_SERVER_KEY='x' * 40)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response['WWW-Authenticate'], 'Bearer')

    def test_missing_server_key_is_forbidden_even_with_token(self):
        routes = self.protected_routes() + [('client-list', None, ('post',))]
        for name, form, methods in routes:
            for method in methods:
                with self.subTest(route=name, method=method):
                    response = getattr(self.client, method)(self.url(name, form),
                        HTTP_AUTHORIZATION=self.headers['HTTP_AUTHORIZATION'])
                    self.assertEqual(response.status_code, 403)

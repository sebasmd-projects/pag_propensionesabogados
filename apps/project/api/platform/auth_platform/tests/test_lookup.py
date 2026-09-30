import re
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.utils.functions.token_utils import generate_token, verify_token, serializer
from apps.common.utils.otp_codes import hash_code
from apps.project.api.platform.auth_platform.models import (
    AttlasInsolvencyAuthModel, ClientLookupChallenge,
)
from apps.project.api.platform.insolvency_form.models import AttlasInsolvencyFormModel


@override_settings(
    SERVER_KEY='x' * 40, SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class ClientLookupTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AttlasInsolvencyAuthModel.objects.create(
            document_number='12345678901', birth_date=date(1990, 2, 3),
        )
        cls.form = AttlasInsolvencyFormModel.objects.create(
            user=cls.user, debtor_first_name='Ana', debtor_last_name='Pérez',
            debtor_email='ana@example.com', debtor_cell_phone='3001234567',
            debtor_address='Calle 10', debtor_birth_date=cls.user.birth_date,
        )
        cls.other_user = AttlasInsolvencyAuthModel.objects.create(
            document_number='98765432109', birth_date=date(1991, 1, 1),
        )
        cls.other_form = AttlasInsolvencyFormModel.objects.create(user=cls.other_user)

    def setUp(self):
        cache.clear()
        self.headers = {'HTTP_X_SERVER_KEY': 'x' * 40}
        self.lookup_url = reverse('api-clients-lookup')
        self.verify_url = reverse('api-clients-lookup-verify')

    def lookup(self, document=None, birth=None, **headers):
        module = 'apps.project.api.platform.auth_platform.api.views'
        with patch(module + '.threading.Thread') as thread, patch(
            module + '.close_old_connections',
        ), self.captureOnCommitCallbacks(execute=True):
            thread.return_value.start.side_effect = lambda: thread.call_args.kwargs['target'](
                *thread.call_args.kwargs['args'])
            return self.client.post(self.lookup_url, {
                'documentNumber': document or self.user.document_number,
                'birthDate': birth or self.user.birth_date.isoformat(),
            }, format='json', **(self.headers | headers))

    def issue(self):
        response = self.lookup()
        self.assertEqual(response.status_code, 202)
        code = re.search(r'(?<![0-9])[0-9]{6}(?![0-9])', mail.outbox[-1].body).group()
        return response.data['challenge_id'], code

    def verify(self, challenge_id, code):
        return self.client.post(self.verify_url, {
            'challenge_id': str(challenge_id), 'code': code,
        }, format='json', **self.headers)

    def lookup_headers(self):
        challenge_id, code = self.issue()
        response = self.verify(challenge_id, code)
        self.assertEqual(response.status_code, 200)
        return self.headers | {'HTTP_AUTHORIZATION': 'Bearer ' + response.data['token']}

    def test_email_contains_code_but_no_document_and_database_only_has_hash(self):
        challenge_id, code = self.issue()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['ana@example.com'])
        self.assertEqual(message.subject, 'Tu código de verificación')
        self.assertIn('10 minutos', message.body)
        self.assertNotIn(self.user.document_number, message.body)
        self.assertNotIn(self.user.document_number, message.alternatives[0][0])
        challenge = ClientLookupChallenge.objects.get(pk=challenge_id)
        self.assertEqual(challenge.auth_user, self.user)
        self.assertEqual(challenge.code_hash, hash_code(code))
        self.assertEqual(len(challenge.code_hash), 64)
        self.assertNotIn(code, str(ClientLookupChallenge.objects.filter(pk=challenge_id).values().get()))
        self.assertAlmostEqual((challenge.expires_at - timezone.now()).total_seconds(), 600, delta=10)

    def test_unknown_client_has_same_keys_without_email(self):
        response = self.lookup(document='unknown')
        self.assertEqual(response.status_code, 202)
        self.assertEqual(set(response.data), {'challenge_id'})
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(ClientLookupChallenge.objects.get(pk=response.data['challenge_id']).auth_user)

    def test_missing_email_has_same_response(self):
        response = self.lookup(self.other_user.document_number, self.other_user.birth_date.isoformat())
        self.assertEqual(response.status_code, 202)
        self.assertEqual(set(response.data), {'challenge_id'})
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(ClientLookupChallenge.objects.get(pk=response.data['challenge_id']).auth_user)

    def test_missing_form_has_same_response(self):
        self.other_form.delete()
        response = self.lookup(self.other_user.document_number, self.other_user.birth_date.isoformat())
        self.assertEqual(response.status_code, 202)
        self.assertEqual(set(response.data), {'challenge_id'})
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_lookup_input_is_400(self):
        for body in ({}, {'documentNumber': '', 'birthDate': '1990-02-03'},
                     {'documentNumber': '123', 'birthDate': 'invalid'}):
            with self.subTest(body=body):
                response = self.client.post(self.lookup_url, body, **self.headers)
                self.assertEqual(response.status_code, 400)
        self.assertEqual(ClientLookupChallenge.objects.count(), 0)

    def test_verify_response_and_single_use(self):
        challenge_id, code = self.issue()
        response = self.verify(challenge_id, code)
        self.assertEqual(response.status_code, 200)
        data = dict(response.data)
        token = data.pop('token')
        self.assertEqual(data, {
            'id': str(self.user.id), 'form_id': str(self.form.id),
            'documentNumber': self.user.document_number, 'birthDate': '1990-02-03',
            'firstName': 'Ana', 'lastName': 'Pérez', 'email': 'ana@example.com',
            'phone': '3001234567', 'address': 'Calle 10',
            'expires_in': settings.ATTLAS_LOOKUP_TOKEN_TIMEOUT,
        })
        self.assertEqual(serializer.loads(token)['scope'], 'lookup')
        self.assertEqual(verify_token(token, scopes=('lookup',)), str(self.user.id))
        self.assertEqual(self.verify(challenge_id, code).status_code, 400)
        challenge = ClientLookupChallenge.objects.get(pk=challenge_id)
        self.assertIsNotNone(challenge.used_at)
        self.assertEqual(challenge.attempts, 1)

    def test_five_failures_kill_challenge(self):
        challenge_id, code = self.issue()
        wrong = '000000' if code != '000000' else '111111'
        for attempt in range(5):
            self.assertEqual(self.verify(challenge_id, wrong).status_code, 400)
            self.assertEqual(ClientLookupChallenge.objects.get(pk=challenge_id).attempts, attempt + 1)
        self.assertEqual(self.verify(challenge_id, code).status_code, 400)
        self.assertEqual(ClientLookupChallenge.objects.get(pk=challenge_id).attempts, 5)

    def test_expired_missing_and_malformed_challenges_have_same_error(self):
        challenge_id, code = self.issue()
        ClientLookupChallenge.objects.filter(pk=challenge_id).update(expires_at=timezone.now())
        for value in (challenge_id, uuid4(), 'bad-uuid'):
            response = self.verify(value, code)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, {'detail': 'Código inválido o caducado.'})

    def test_dummy_challenge_cannot_issue_token_even_with_matching_code(self):
        challenge = ClientLookupChallenge.objects.create(
            code_hash=hash_code('123456'), expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertEqual(self.verify(challenge.id, '123456').status_code, 400)
        challenge.refresh_from_db()
        self.assertEqual(challenge.attempts, 1)
        self.assertIsNone(challenge.used_at)

    def test_fourth_document_lookup_is_limited_even_from_different_ip(self):
        for index in range(4):
            response = self.lookup(document=' Unknown ' if index % 2 else 'unknown',
                                   REMOTE_ADDR=f'192.0.2.{index + 1}')
            self.assertEqual(response.status_code, 202 if index < 3 else 429)
        self.assertEqual(response.data, {'detail': 'Demasiadas solicitudes. Intente más tarde.'})
        self.assertEqual(ClientLookupChallenge.objects.count(), 3)

    def test_lookup_ip_quota(self):
        for index in range(11):
            response = self.lookup(document=f'unknown-{index}')
            self.assertEqual(response.status_code, 202 if index < 10 else 429)

    def test_both_lookup_buckets_are_always_consumed(self):
        module = 'apps.project.api.platform.auth_platform.api.views'
        with patch(module + '.clients_lookup_ip.consume', return_value=False) as ip, patch(
            module + '.clients_lookup_doc.consume', return_value=True,
        ) as doc:
            self.assertEqual(self.lookup().status_code, 429)
        ip.assert_called_once()
        doc.assert_called_once()

    def test_broken_cache_fails_closed(self):
        with patch('apps.common.utils.throttling.cache.incr', return_value=None):
            self.assertEqual(self.lookup().status_code, 429)
            self.assertEqual(self.verify(uuid4(), '123456').status_code, 429)
        self.assertEqual(ClientLookupChallenge.objects.count(), 0)

    def test_verify_ip_quota(self):
        for index in range(31):
            response = self.verify(uuid4(), '123456')
            self.assertEqual(response.status_code, 400 if index < 30 else 429)

    def test_delivery_failure_is_logged_and_does_not_change_response(self):
        with patch('apps.project.api.platform.auth_platform.emails.EmailMultiAlternatives.send',
                   side_effect=RuntimeError('mail unavailable')), self.assertLogs(
                       'apps.project.api.platform.auth_platform.emails', level='ERROR'):
            response = self.lookup()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(set(response.data), {'challenge_id'})

    def test_worker_exception_is_logged_and_response_is_202(self):
        module = 'apps.project.api.platform.auth_platform.api.views'
        with patch(module + '.send_lookup_code', side_effect=RuntimeError('failed')), self.assertLogs(
            module, level='ERROR',
        ):
            self.assertEqual(self.lookup().status_code, 202)

    def test_email_is_scheduled_only_after_commit_without_waiting_for_worker(self):
        module = 'apps.project.api.platform.auth_platform.api.views'
        with patch(module + '.threading.Thread') as thread, patch(module + '.send_lookup_code') as send:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.lookup_url, {
                    'documentNumber': self.user.document_number,
                    'birthDate': self.user.birth_date.isoformat(),
                }, **self.headers)
                self.assertEqual(response.status_code, 202)
                thread.assert_not_called()
            self.assertTrue(thread.call_args.kwargs['daemon'])
            thread.return_value.start.assert_called_once_with()
            send.assert_not_called()
            with patch(module + '.close_old_connections') as close:
                thread.call_args.kwargs['target'](*thread.call_args.kwargs['args'])
                close.assert_called_once_with()
            send.assert_called_once_with('ana@example.com', thread.call_args.kwargs['args'][1])

    def test_lookup_token_can_read_and_update_only_own_calculator_form(self):
        headers = self.lookup_headers()
        for form, expected in ((self.form, 200), (self.other_form, 404)):
            url = reverse('calculator_api:client-detail', kwargs={'pk': form.id})
            for method in ('get', 'patch', 'put'):
                with self.subTest(form=form.id, method=method):
                    response = getattr(self.client, method)(url, {'firstName': 'María'}, **headers)
                    self.assertEqual(response.status_code, expected)
        self.form.refresh_from_db()
        self.other_form.refresh_from_db()
        self.assertEqual(self.form.debtor_first_name, 'María')
        self.assertNotEqual(self.other_form.debtor_first_name, 'María')

    def test_lookup_token_cannot_access_wizard_or_signature(self):
        headers = self.lookup_headers()
        for name, kwargs, methods in (
            ('wizard', {'id': self.form.id}, ('get', 'patch', 'put')),
            ('wizard-me', {}, ('get', 'patch', 'put')),
            ('signature-update', {'id': self.form.id}, ('get', 'patch', 'put')),
            ('signature-create', {}, ('post',)),
        ):
            for method in methods:
                with self.subTest(route=name, method=method):
                    response = getattr(self.client, method)(
                        reverse('insolvency_form_api:' + name, kwargs=kwargs), {}, **headers,
                    )
                    self.assertIn(response.status_code, (401, 403))

    def test_platform_and_legacy_tokens_still_work_in_wizard(self):
        for token in (generate_token(str(self.user.id)), serializer.dumps({'user_id': str(self.user.id)})):
            headers = self.headers | {'HTTP_AUTHORIZATION': 'Bearer ' + token}
            for name, kwargs in (('wizard', {'id': self.form.id}), ('wizard-me', {})):
                response = self.client.get(reverse('insolvency_form_api:' + name, kwargs=kwargs), **headers)
                self.assertEqual(response.status_code, 200)

    @override_settings(ATTLAS_LOOKUP_TOKEN_TIMEOUT=60)
    def test_lookup_token_lifetime_uses_setting(self):
        with patch('itsdangerous.timed.TimestampSigner.get_timestamp', return_value=1000):
            lookup = generate_token(str(self.user.id), scope='lookup')
            platform = generate_token(str(self.user.id))
        with patch('itsdangerous.timed.TimestampSigner.get_timestamp', return_value=1061):
            with self.assertRaisesMessage(ValueError, 'Token expirado'):
                verify_token(lookup, max_age=9999, scopes=('lookup',))
            self.assertEqual(verify_token(platform, max_age=9999), str(self.user.id))
            response = self.client.get(reverse('calculator_api:client-detail', kwargs={'pk': self.form.id}),
                **(self.headers | {'HTTP_AUTHORIZATION': 'Bearer ' + lookup}))
            self.assertEqual(response.status_code, 401)

    def test_scope_rejection_and_legacy_default(self):
        for scope in ('lookup', 'unknown', None):
            with self.assertRaisesMessage(ValueError, 'Token inválido'):
                verify_token(generate_token(str(self.user.id), scope=scope))
        self.assertEqual(verify_token(serializer.dumps({'user_id': str(self.user.id)})), str(self.user.id))

    def test_server_key_required_for_both_routes(self):
        for url in (self.lookup_url, self.verify_url):
            self.assertEqual(self.client.post(url, {}).status_code, 403)

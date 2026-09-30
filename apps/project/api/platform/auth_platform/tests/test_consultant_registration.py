import re
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.hashers import make_password
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.utils.otp_codes import hash_code
from apps.project.api.platform.auth_platform.models import (
    AttlasInsolvencyAuthConsultantsModel as Consultant,
    AttlasInsolvencyAuthModel,
    ConsultantRegistrationChallenge as Challenge,
)


MODULE = 'apps.project.api.platform.auth_platform.api.views'
PASSWORD = 'Una-Clave-Segura!739'
INVALID = {'detail': 'Código inválido o caducado.'}


@override_settings(
    SERVER_KEY='x' * 40, SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class ConsultantRegistrationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_user = AttlasInsolvencyAuthModel.objects.create(
            document_number='12345678901', birth_date=date(1990, 2, 3),
        )

    def setUp(self):
        cache.clear()
        self.headers = {'HTTP_X_SERVER_KEY': 'x' * 40}
        self.register_url = reverse('api-insolvency-consultants-register')
        self.verify_url = reverse('api-insolvency-consultants-register-verify')
        self.payload = {
            'first_name': 'Juan Sebastian', 'last_name': 'Martinez Diaz',
            'email': 'juan@propensionesabogados.com',
            'password': PASSWORD, 'password_confirm': PASSWORD,
        }

    def register(self, *, headers=None, **changes):
        with patch(MODULE + '.threading.Thread') as thread, patch(
            MODULE + '.close_old_connections',
        ), self.captureOnCommitCallbacks(execute=True):
            thread.return_value.start.side_effect = lambda: thread.call_args.kwargs['target'](
                *thread.call_args.kwargs['args'])
            return self.client.post(self.register_url, self.payload | changes,
                                    format='json', **(self.headers if headers is None else headers))

    def issue(self, **changes):
        response = self.register(**changes)
        self.assertEqual(response.status_code, 202, response.data)
        code = re.search(r'(?<![0-9])[0-9]{6}(?![0-9])', mail.outbox[-1].body).group()
        return response.data['challenge_id'], code

    def verify(self, challenge_id, code):
        return self.client.post(self.verify_url, {
            'challenge_id': str(challenge_id), 'code': code,
        }, format='json', **self.headers)

    def login(self, user, password=PASSWORD):
        return self.client.post(reverse('api-insolvency-login'), {
            'document_number': self.client_user.document_number,
            'birth_date': self.client_user.birth_date.isoformat(),
            'user': user, 'password': password,
        }, format='json', **self.headers)

    def assert_login_failure(self, consultant):
        with patch('apps.project.api.platform.auth_platform.api.serializers.note_failure') as failure, patch.object(
            Consultant, 'check_password', autospec=True, return_value=True,
        ) as check:
            response = self.login(consultant.user)
            self.assertEqual(response.status_code, 400)
            failure.assert_called_once()
            check.assert_called_once()
        unknown = self.login('UNKNOWN')
        self.assertEqual(response.data, unknown.data)

    def test_rejects_other_domains_and_subdomains(self):
        for domain in ('gmail.com', 'sub.propensionesabogados.com'):
            with self.subTest(domain=domain):
                response = self.register(email='juan@' + domain)
                self.assertEqual(response.status_code, 400)
                self.assertIn('email', response.data)
        self.assertFalse(Consultant.objects.exists())

    def test_accepts_all_three_domains(self):
        for domain in ('propensionesabogados.com', 'fundacionattlas.com', 'fundacionattlas.org'):
            self.assertEqual(self.register(email='juan@' + domain).status_code, 202)

    @override_settings(ATTLAS_CONSULTANT_EMAIL_DOMAINS=('corporativo.example',))
    def test_domain_setting_is_used(self):
        self.assertEqual(self.register().status_code, 400)
        self.assertEqual(self.register(email='juan@corporativo.example').status_code, 202)

    def test_password_confirmation(self):
        response = self.register(password_confirm='Otra clave')
        self.assertEqual(response.status_code, 400)
        self.assertIn('password_confirm', response.data)

    def test_weak_password(self):
        response = self.register(password='123', password_confirm='123')
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_empty_names(self):
        for field in ('first_name', 'last_name'):
            response = self.register(**{field: '   '})
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.data)

    def test_registration_email_verification_and_login(self):
        challenge_id, code = self.issue(email='  JUAN@PROPENSIONESABOGADOS.COM  ')
        consultant = Consultant.objects.get()
        self.assertFalse(consultant.is_active)
        self.assertIsNone(consultant.email_verified_at)
        self.assertEqual(consultant.first_name, 'JUAN SEBASTIAN')
        self.assertEqual(consultant.last_name, 'MARTINEZ DIAZ')
        self.assertEqual(consultant.email, self.payload['email'])
        self.assertTrue(consultant.check_password(PASSWORD))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Verifica tu correo')
        self.assertEqual(message.to, [consultant.email])
        self.assertIn('10 minutos', message.body)
        for sensitive in (PASSWORD, consultant.first_name, self.client_user.document_number):
            self.assertNotIn(sensitive, message.body)
            self.assertNotIn(sensitive, message.alternatives[0][0])
        challenge = Challenge.objects.get(pk=challenge_id)
        self.assertEqual(challenge.code_hash, hash_code(code))
        self.assertAlmostEqual((challenge.expires_at - timezone.now()).total_seconds(), 600, delta=10)
        response = self.verify(challenge_id, code)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'user': 'JSMD', 'email': consultant.email})
        consultant.refresh_from_db()
        self.assertTrue(consultant.is_active)
        self.assertIsNotNone(consultant.email_verified_at)
        self.assertEqual(self.login(consultant.user).status_code, 200)

    def test_pending_consultant_cannot_login(self):
        self.issue()
        consultant = Consultant.objects.get()
        self.assertEqual(self.login(consultant.user).status_code, 400)
        self.assert_login_failure(consultant)

    def test_disabled_consultant_cannot_login(self):
        consultant = Consultant.objects.create(first_name='Ana', last_name='Perez',
            password=PASSWORD, is_active=False, email_verified_at=timezone.now())
        self.assertEqual(self.login(consultant.user).status_code, 400)
        self.assert_login_failure(consultant)

    def test_legacy_consultant_without_email_can_login(self):
        consultant = Consultant.objects.create(first_name='Ana', last_name='Perez', password=PASSWORD)
        self.assertIsNone(consultant.email)
        self.assertTrue(consultant.is_active)
        self.assertEqual(self.login(consultant.user).status_code, 200)

    def test_verified_email_creates_only_ghost_challenge(self):
        consultant = Consultant.objects.create(first_name='Ana', last_name='Perez', password=PASSWORD,
            email=self.payload['email'], email_verified_at=timezone.now(), is_active=False)
        before = Consultant.objects.values().get(pk=consultant.pk)
        response = self.register()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(set(response.data), {'challenge_id'})
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Consultant.objects.count(), 1)
        self.assertEqual(Consultant.objects.values().get(pk=consultant.pk), before)
        self.assertIsNone(Challenge.objects.get(pk=response.data['challenge_id']).consultant_id)

    def test_pending_registration_is_updated_and_old_code_revoked(self):
        old_id, old_code = self.issue()
        consultant = Consultant.objects.get()
        new_password = 'Otra-Clave-Segura!839'
        new_id, new_code = self.issue(first_name='Jose', password=new_password, password_confirm=new_password)
        self.assertEqual(Consultant.objects.count(), 1)
        consultant.refresh_from_db()
        self.assertEqual(consultant.first_name, 'JOSE')
        self.assertTrue(consultant.check_password(new_password))
        self.assertFalse(consultant.is_active)
        self.assertEqual(self.verify(old_id, old_code).data, INVALID)
        self.assertEqual(self.verify(new_id, new_code).status_code, 200)

    def test_repeated_initials_receive_suffix(self):
        self.issue()
        challenge_id, code = self.issue(email='otro@fundacionattlas.com')
        self.assertEqual(self.verify(challenge_id, code).data['user'], 'JSMD2')
        self.issue(email='tercero@fundacionattlas.org')
        self.assertTrue(Consultant.objects.filter(user='JSMD3').exists())

    def test_initials_never_exceed_field_length(self):
        for index in range(3):
            consultant = Consultant.objects.create(first_name=' '.join(['Juan'] * 16), last_name='Diaz')
            self.assertLessEqual(len(consultant.user), 15)
        self.assertTrue(consultant.user.endswith('3'))

    def test_model_normalizes_email_and_preserves_hash_on_admin_edits(self):
        consultant = Consultant.objects.create(first_name='Ana', last_name='Perez',
            password=PASSWORD, email='  ANA@FUNDACIONATTLAS.COM ')
        self.assertEqual(consultant.email, 'ana@fundacionattlas.com')
        original = consultant.password
        consultant.is_active = False
        consultant.save()
        self.assertEqual(consultant.password, original)
        consultant.password = 'Nueva-Clave!987'
        consultant.save()
        consultant.refresh_from_db()
        self.assertTrue(consultant.check_password('Nueva-Clave!987'))

    def test_other_supported_password_hash_is_not_hashed_again(self):
        encoded = make_password(PASSWORD, hasher='pbkdf2_sha256')
        consultant = Consultant.objects.create(first_name='Ana', last_name='Perez', password=encoded)
        consultant.save()
        self.assertEqual(consultant.password, encoded)
        self.assertTrue(consultant.check_password(PASSWORD))

    def test_used_challenge_cannot_reactivate_disabled_consultant(self):
        challenge_id, code = self.issue()
        self.assertEqual(self.verify(challenge_id, code).status_code, 200)
        Consultant.objects.update(is_active=False)
        response = self.verify(challenge_id, code)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, INVALID)
        self.assertFalse(Consultant.objects.get().is_active)

    def test_expired_missing_and_malformed_challenges(self):
        challenge_id, code = self.issue()
        Challenge.objects.filter(pk=challenge_id).update(expires_at=timezone.now())
        for value in (challenge_id, uuid4(), 'bad-uuid'):
            response = self.verify(value, code)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, INVALID)
        self.assertEqual(self.verify(challenge_id, 'not-a-code').data, INVALID)

    def test_five_failed_attempts(self):
        challenge_id, code = self.issue()
        wrong = '000000' if code != '000000' else '111111'
        for attempt in range(5):
            response = self.verify(challenge_id, wrong)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, INVALID)
            self.assertEqual(Challenge.objects.get(pk=challenge_id).attempts, attempt + 1)
        self.assertEqual(self.verify(challenge_id, code).data, INVALID)
        self.assertEqual(Challenge.objects.get(pk=challenge_id).attempts, 5)
        self.assertFalse(Consultant.objects.get().is_active)

    def test_ghost_cannot_be_verified_even_with_correct_code(self):
        challenge = Challenge.objects.create(code_hash=hash_code('123456'),
            expires_at=timezone.now() + timedelta(minutes=10))
        self.assertEqual(self.verify(challenge.pk, '123456').data, INVALID)
        challenge.refresh_from_db()
        self.assertEqual(challenge.attempts, 1)
        self.assertIsNone(challenge.used_at)

    def test_email_quota_is_normalized_and_independent_of_ip(self):
        for index in range(4):
            response = self.register(email=self.payload['email'].upper() if index % 2 else self.payload['email'],
                headers=self.headers | {'REMOTE_ADDR': f'192.0.2.{index + 1}'})
            self.assertEqual(response.status_code, 202 if index < 3 else 429)
        self.assertEqual(Challenge.objects.count(), 3)
        self.assertEqual(len(mail.outbox), 3)

    def test_register_ip_quota(self):
        for index in range(11):
            response = self.register(email=f'juan{index}@fundacionattlas.org')
            self.assertEqual(response.status_code, 202 if index < 10 else 429)

    def test_verify_ip_quota(self):
        for index in range(31):
            response = self.verify(uuid4(), '123456')
            self.assertEqual(response.status_code, 400 if index < 30 else 429)

    def test_both_register_buckets_are_consumed(self):
        with patch(MODULE + '.consultant_register_ip.consume', return_value=False) as ip, patch(
            MODULE + '.consultant_register_email.consume', return_value=True,
        ) as email:
            self.assertEqual(self.register().status_code, 429)
        ip.assert_called_once()
        self.assertEqual(email.call_args.kwargs['scope'], self.payload['email'])

    def test_cache_failure_is_closed(self):
        with patch('apps.common.utils.throttling.cache.incr', return_value=None):
            self.assertEqual(self.register().status_code, 429)
            self.assertEqual(self.verify(uuid4(), '123456').status_code, 429)
        self.assertFalse(Consultant.objects.exists())
        self.assertFalse(Challenge.objects.exists())

    def test_email_thread_starts_only_after_commit(self):
        with patch(MODULE + '.threading.Thread') as thread, patch(MODULE + '.send_consultant_registration_code') as send:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.register_url, self.payload, **self.headers)
                self.assertEqual(response.status_code, 202)
                thread.assert_not_called()
            self.assertTrue(thread.call_args.kwargs['daemon'])
            thread.return_value.start.assert_called_once_with()
            send.assert_not_called()
            with patch(MODULE + '.close_old_connections') as close:
                thread.call_args.kwargs['target'](*thread.call_args.kwargs['args'])
                close.assert_called_once_with()
            send.assert_called_once()

    def test_email_failure_does_not_change_response(self):
        with patch('apps.project.api.platform.auth_platform.emails.EmailMultiAlternatives.send',
                   side_effect=RuntimeError('unavailable')), self.assertLogs(
                       'apps.project.api.platform.auth_platform.emails', level='ERROR'):
            self.assertEqual(self.register().status_code, 202)

    def test_server_key_required_for_both_routes(self):
        for url in (self.register_url, self.verify_url):
            self.assertEqual(self.client.post(url, {}, format='json').status_code, 403)

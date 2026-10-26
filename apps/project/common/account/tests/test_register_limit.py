# apps/project/common/account/tests/test_register_limit.py
"""
El alta de cuenta esta abierta a cualquiera, asi que tiene cupo por IP. Sin el
se crean cuentas a golpes y los errores de validacion sirven de oraculo para
saber que usuarios existen (`check_security` §2 lo marcaba).

    manage.py test apps.project.common.account.tests.test_register_limit
"""

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.common.utils.testing import dead_cache
from apps.project.common.users.models import UserModel

from ..views import UserRegisterView

PER_IP = UserRegisterView.REGISTER_MAX_PER_IP
SOMEONE = '203.0.113.30'
SOMEONE_ELSE = '203.0.113.31'


class RegisterLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('account:register')

    def post(self, n=0, ip=SOMEONE):
        # Un cuerpo incompleto basta: el cupo se apunta antes de validar.
        return self.client.post(
            self.url,
            {'first_name': 'Ana', 'username': f'ana{n}', 'password': 'x'},
            REMOTE_ADDR=ip,
        )

    def test_the_request_after_the_quota_is_rejected(self):
        for number in range(PER_IP):
            self.assertNotEqual(self.post(number).status_code, 429, number)

        response = self.post(PER_IP)

        self.assertEqual(response.status_code, 429)
        self.assertContains(
            response, 'Too many sign-up attempts', status_code=429)

    def test_a_valid_signup_over_the_quota_creates_nothing(self):
        for number in range(PER_IP):
            self.post(number)

        before = UserModel.objects.count()
        response = self.client.post(self.url, {
            'first_name': 'Ana', 'last_name': 'Perez', 'username': 'valida',
            'email': 'valida@example.com', 'password': 'pw-for-tests-123',
            'confirm_password': 'pw-for-tests-123',
        }, REMOTE_ADDR=SOMEONE)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(UserModel.objects.count(), before)

    def test_the_quota_is_per_ip(self):
        for number in range(PER_IP + 1):
            self.post(number)

        self.assertEqual(self.post(99).status_code, 429)
        self.assertNotEqual(self.post(99, SOMEONE_ELSE).status_code, 429)

    def test_a_dead_cache_rejects(self):
        with dead_cache():
            self.assertEqual(self.post().status_code, 429)

    def test_viewing_the_form_costs_nothing(self):
        for _ in range(PER_IP + 3):
            self.assertEqual(
                self.client.get(self.url, REMOTE_ADDR=SOMEONE).status_code,
                200,
            )

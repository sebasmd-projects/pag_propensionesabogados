# apps/common/core/tests/test_contact_limit.py
"""
El formulario de contacto tiene dos puertas -- la portada y la API -- y un
solo cupo por IP. Antes no tenia ninguno: `check_security` §2 lo marcaba, y
la portada manda un correo de confirmacion a la direccion que se escriba, asi
que repetirlo era una forma de llenar la bandeja de otro.

    manage.py test apps.common.core.tests.test_contact_limit
"""

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.common.utils.testing import dead_cache

from ..models import ContactModel
from ..throttling import CONTACT_MAX_PER_IP

SOMEONE = '203.0.113.20'
SOMEONE_ELSE = '203.0.113.21'


def api_payload(n=0):
    return {
        'name': 'Ana',
        'last_name': 'Perez',
        'email': f'ana{n}@example.com',
        'subject': 'Consulta',
        'message': 'Hola, quisiera una cita.',
    }


class IndexContactLimitTests(TestCase):
    """`core:index` (el POST de la portada)."""

    def setUp(self):
        cache.clear()
        self.url = reverse('core:index')

    def post(self, ip=SOMEONE):
        # Sin captcha ni nada valido: el cupo se apunta antes de validar, y
        # asi la prueba no sale a Google.
        # El campo trampa llega vacio, como en un navegador: sin el, el
        # decorador de la trampa responde 400 antes de llegar al cupo.
        return self.client.post(
            self.url,
            {
                'name': 'Ana',
                'message': 'texto largo',
                settings.HONEYPOT_FIELD_NAME: '',
            },
            REMOTE_ADDR=ip,
        )

    def test_the_request_after_the_quota_is_rejected(self):
        for number in range(CONTACT_MAX_PER_IP):
            self.assertNotEqual(self.post().status_code, 429, number)

        response = self.post()

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'Too many messages', status_code=429)

    def test_the_rejected_form_keeps_what_was_typed(self):
        for _ in range(CONTACT_MAX_PER_IP):
            self.post()

        response = self.post()

        self.assertContains(response, 'texto largo', status_code=429)

    def test_the_quota_is_per_ip(self):
        for _ in range(CONTACT_MAX_PER_IP + 1):
            self.post()

        self.assertEqual(self.post().status_code, 429)
        self.assertNotEqual(self.post(SOMEONE_ELSE).status_code, 429)

    def test_a_dead_cache_rejects_instead_of_letting_everything_through(self):
        """Falla cerrado: el limite es lo que protege el buzon de un tercero."""
        with dead_cache():
            self.assertEqual(self.post().status_code, 429)

    def test_a_rejected_request_sends_no_mail(self):
        for _ in range(CONTACT_MAX_PER_IP + 3):
            self.post()

        self.assertEqual(mail.outbox, [])


class ContactApiLimitTests(TestCase):
    """`api-contact-create`, que es lo que llama el frontend."""

    def setUp(self):
        cache.clear()
        self.url = reverse('api-contact-create')

    def post(self, n=0, ip=SOMEONE):
        return self.client.post(
            self.url, api_payload(n), REMOTE_ADDR=ip,
            content_type='application/json',
        )

    def test_the_request_after_the_quota_is_rejected(self):
        for number in range(CONTACT_MAX_PER_IP):
            self.assertEqual(self.post(number).status_code, 201, number)

        response = self.post(CONTACT_MAX_PER_IP)

        self.assertEqual(response.status_code, 429)
        self.assertIn('detail', response.json())
        self.assertEqual(ContactModel.objects.count(), CONTACT_MAX_PER_IP)

    def test_the_quota_is_per_ip(self):
        for number in range(CONTACT_MAX_PER_IP + 1):
            self.post(number)

        self.assertEqual(self.post(99).status_code, 429)
        self.assertEqual(self.post(99, SOMEONE_ELSE).status_code, 201)

    def test_a_dead_cache_rejects(self):
        with dead_cache():
            self.assertEqual(self.post().status_code, 429)

        self.assertEqual(ContactModel.objects.count(), 0)

    def test_both_doors_share_one_quota(self):
        """Repartir los envios entre la portada y la API no da el doble."""
        half = CONTACT_MAX_PER_IP // 2

        for number in range(half):
            self.post(number)

        for _ in range(CONTACT_MAX_PER_IP - half):
            self.client.post(
                reverse('core:index'),
                {'name': 'Ana', settings.HONEYPOT_FIELD_NAME: ''},
                REMOTE_ADDR=SOMEONE,
            )

        self.assertEqual(self.post(99).status_code, 429)

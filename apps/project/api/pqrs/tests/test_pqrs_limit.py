# apps/project/api/pqrs/tests/test_pqrs_limit.py
"""
Radicar una PQRS no necesita cuenta, asi que el cupo es por IP. Antes no habia
ninguno (`check_security` §2 lo marcaba).

    manage.py test apps.project.api.pqrs
"""

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.common.utils.testing import dead_cache

from ..api.views import pqrs_by_ip
from ..models import PQRSModel

SOMEONE = '203.0.113.40'
SOMEONE_ELSE = '203.0.113.41'
QUOTA = pqrs_by_ip.limit


def payload(n=0):
    return {
        'request_type': PQRSModel.RequestTypeChoicesEN.OTHER,
        'name': 'Ana',
        'surname': 'Perez',
        'id_number': f'1000{n}',
        'country': 'Colombia',
        'city': 'Bogota',
        'email': f'ana{n}@example.com',
        'cell_prefix': '+57',
        'cellphone': '3001234567',
        'description': 'Quisiera presentar una peticion.',
    }


class PqrsLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('api-pqrs-create')

    def post(self, n=0, ip=SOMEONE):
        return self.client.post(
            self.url, payload(n), REMOTE_ADDR=ip,
            content_type='application/json',
        )

    def test_the_request_after_the_quota_is_rejected(self):
        for number in range(QUOTA):
            self.assertEqual(self.post(number).status_code, 201, number)

        response = self.post(QUOTA)

        self.assertEqual(response.status_code, 429)
        self.assertIn('detail', response.json())
        self.assertEqual(PQRSModel.objects.count(), QUOTA)

    def test_the_quota_is_per_ip(self):
        for number in range(QUOTA + 1):
            self.post(number)

        self.assertEqual(self.post(99).status_code, 429)
        self.assertEqual(self.post(99, SOMEONE_ELSE).status_code, 201)

    def test_a_dead_cache_does_not_close_the_channel(self):
        """
        Falla abierto, y es deliberado: ver el comentario de `pqrs_by_ip`.
        Fijarlo evita que alguien lo cambie sin leer por que.
        """
        with dead_cache():
            self.assertEqual(self.post().status_code, 201)

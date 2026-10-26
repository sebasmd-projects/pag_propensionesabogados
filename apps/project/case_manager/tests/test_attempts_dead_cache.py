"""
Contar los fallos del portal cuando la cache es Redis y esta caida.

Con `django-redis` e `IGNORE_EXCEPTIONS`, un Redis inalcanzable no lanza:
devuelve `None`. El contador anterior leia con `cache.get(key, 0) + 1`, asi que
daba siempre 1 y el limite que sostiene la clave del portal (la inicial del
nombre mas cuatro digitos de la cedula) dejaba de contar sin avisar. Falla
cerrado, como `RateLimit`: sin poder contar, el fallo cuenta como el ultimo.

    manage.py test apps.project.case_manager.tests.test_attempts_dead_cache
"""

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.common.utils.models import IPBlockedModel
from app_core.tests.test_cache_settings import DEAD_REDIS

from .. import attempts

IP = '203.0.113.60'


class CountingWithALiveCacheTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_it_counts_and_blocks_at_the_ceiling(self):
        ceiling = attempts.max_attempts()

        counts = [attempts.register_failure(IP) for _ in range(ceiling)]

        self.assertEqual(counts, list(range(1, ceiling + 1)))
        self.assertTrue(attempts.is_blocked(IP))

    def test_below_the_ceiling_nobody_is_blocked(self):
        attempts.register_failure(IP)

        self.assertFalse(attempts.is_blocked(IP))


@override_settings(CACHES=DEAD_REDIS)
class CountingWithADeadRedisTests(TestCase):

    def test_a_failure_that_cannot_be_counted_blocks_instead_of_passing(self):
        attempts.register_failure(IP)

        self.assertTrue(attempts.is_blocked(IP))
        self.assertEqual(IPBlockedModel.objects.filter(current_ip=IP).count(), 1)

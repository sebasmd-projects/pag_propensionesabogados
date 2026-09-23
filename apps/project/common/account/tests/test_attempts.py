"""
Que las dos puertas cuentan en el mismo sitio, y que pedir codigos tiene tope.

Lo que se comprueba es lo que no se ve: que un codigo equivocado gasta los
mismos intentos que una contrasena equivocada. Si no, el tope de cinco
intentos por codigo se esquiva **pidiendo otro codigo**, y quien tantea puede
alternar de puerta sin acercarse nunca al limite de ninguna.
"""

from unittest.mock import patch

from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.common.utils.axes_hooks import username as axes_username
from apps.common.utils.throttling import RateLimit

from .. import otp_login
from ..login_view import SEND_ACTION

User = get_user_model()

PASSWORD = 'una-contrasena-larga-de-verdad'


class AxesKnowsWhoFailedTests(TestCase):
    """
    `axes` busca un campo `username` en el POST y el asistente lo llama
    `auth-username`. Sin el enganche, cada fallo se guarda con
    `username=None`: el bloqueo por (IP, usuario) degrada en silencio a
    bloqueo por IP --la oficina entera fuera-- y, al reves, quien luego llega
    con la contrasena buena se consulta como una pareja sin fallos y entra
    pese al bloqueo.
    """

    def setUp(self):
        cache.clear()
        AccessAttempt.objects.all().delete()
        self.url = reverse('account:login')
        User.objects.create_user(
            username='ana', email='ana@propensionesabogados.com',
            password=PASSWORD, first_name='Ana', last_name='Prueba',
        )

    def test_el_fallo_se_guarda_con_el_usuario(self):
        self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'auth-username': 'Ana',
            'auth-password': 'la-que-no-es',
        })

        intento = AccessAttempt.objects.get()

        # En minusculas: asi «Ana» y « ana » cuentan como el mismo intento y
        # no abren dos cuentas atras distintas para la misma persona.
        self.assertEqual(intento.username, 'ana')

    def test_el_enganche_normaliza(self):
        self.assertEqual(axes_username(None, {'username': '  Ana  '}), 'ana')

    def test_el_enganche_lee_el_campo_del_asistente(self):
        peticion = self.client.request().wsgi_request
        peticion.POST = {'auth-username': 'Ana'}

        self.assertEqual(axes_username(peticion), 'ana')


class FailuresAreSharedTests(TestCase):
    """Un codigo equivocado cuenta igual que una contrasena equivocada."""

    def setUp(self):
        cache.clear()
        AccessAttempt.objects.all().delete()
        self.url = reverse('account:login')
        User.objects.create_user(
            username='ana', email='ana@propensionesabogados.com',
            password=PASSWORD, first_name='Ana', last_name='Prueba',
        )

    def _pedir_codigo(self):
        self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'use_otp': '1',
        })

        with patch.object(otp_login, 'generate_code', return_value='123456'):
            self.client.post(self.url, {
                'login_view-current_step': 'otp',
                'otp-identifier': 'ana',
                SEND_ACTION: '1',
            })

    def test_un_codigo_equivocado_gasta_intento(self):
        self._pedir_codigo()

        self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            'otp-code': '000000',
        })

        self.assertEqual(
            AccessAttempt.objects.filter(username='ana').count(), 1
        )

    @override_settings(AXES_FAILURE_LIMIT=2)
    def test_al_llegar_al_tope_el_codigo_bueno_ya_no_entra(self):
        """
        El freno se aplica **antes** de mirar el codigo. Al reves se apuntarian
        los fallos sin frenar nada, que es tanto como no tener freno.
        """
        self._pedir_codigo()

        for _ in range(2):
            self.client.post(self.url, {
                'login_view-current_step': 'otp',
                'otp-identifier': 'ana',
                'otp-code': '000000',
            })

        response = self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            'otp-code': '123456',
        })

        self.assertFalse(response.context['user'].is_authenticated)

    @override_settings(AXES_FAILURE_LIMIT=10)
    def test_sin_llegar_al_tope_el_codigo_bueno_si_entra(self):
        """
        El control de la prueba anterior. Sin el, aquella pasaria igual si el
        codigo dejara de servir por cualquier otro motivo --por ejemplo si dos
        fallos lo quemaran-- y no estaria probando el freno.
        """
        self._pedir_codigo()

        for _ in range(2):
            self.client.post(self.url, {
                'login_view-current_step': 'otp',
                'otp-identifier': 'ana',
                'otp-code': '000000',
            })

        response = self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            'otp-code': '123456',
        }, follow=True)

        self.assertTrue(response.context['user'].is_authenticated)


class SendThrottleTests(TestCase):
    """Pedir codigos tiene tope, y el tope es del buzon."""

    def setUp(self):
        cache.clear()
        self.url = reverse('account:login')
        User.objects.create_user(
            username='ana', email='ana@propensionesabogados.com',
            password=PASSWORD, first_name='Ana', last_name='Prueba',
        )

    def _pedir(self, identificador='ana'):
        self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': identificador,
            SEND_ACTION: '1',
        })

    def test_no_se_pueden_pedir_infinitos(self):
        for _ in range(6):
            self._pedir()

        self.assertLessEqual(len(mail.outbox), otp_login.send_throttle.limit)

    def test_el_cupo_es_del_buzon_y_no_de_lo_que_se_teclea(self):
        """
        Pedir el codigo una vez por el usuario y otra por el correo son dos
        formas de escribir la misma cuenta: si abrieran dos cupos, el tope se
        duplicaria con solo cambiar lo que se escribe.
        """
        for _ in range(3):
            self._pedir('ana')

        mail.outbox.clear()
        self._pedir('ana@propensionesabogados.com')

        self.assertEqual(len(mail.outbox), 0)


class RateLimitTests(TestCase):
    """El cubo de intentos, por separado."""

    def setUp(self):
        cache.clear()

    def test_deja_pasar_hasta_el_tope(self):
        limite = RateLimit('prueba', limit=3, window=60)
        peticion = self.client.request().wsgi_request

        self.assertEqual(
            [limite.consume(peticion) for _ in range(4)],
            [True, True, True, False],
        )

    def test_dos_ambitos_no_comparten_cupo(self):
        limite = RateLimit('prueba', limit=1, window=60)
        peticion = self.client.request().wsgi_request

        self.assertTrue(limite.consume(peticion, scope='uno@example.com'))
        self.assertTrue(limite.consume(peticion, scope='dos@example.com'))
        self.assertFalse(limite.consume(peticion, scope='uno@example.com'))

    def test_el_ambito_no_se_guarda_en_claro(self):
        """
        Una llave de cache es un sitio donde nadie espera encontrar datos
        personales: quedan en Redis, salen en un `KEYS` y sobreviven al
        proceso.
        """
        limite = RateLimit('prueba', limit=1, window=60)
        llave = limite.key_for(None, scope='ana@propensionesabogados.com')

        self.assertNotIn('ana', llave)
        self.assertNotIn('@', llave)

    def test_si_la_cache_no_responde_se_rechaza(self):
        """
        Falla **cerrado**. Aqui el limite no evita una molestia pasajera: es
        lo unico que impide llenar el buzon de un tercero a base de pedirle
        codigos, y eso no se acaba cuando se acaba la averia.
        """
        limite = RateLimit('prueba', limit=3, window=60)
        peticion = self.client.request().wsgi_request

        with patch('apps.common.utils.throttling.cache.incr',
                   side_effect=ConnectionError('sin cache')):
            self.assertFalse(limite.consume(peticion))

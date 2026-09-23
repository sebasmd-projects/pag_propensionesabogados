"""
Que la puerta del codigo **no** es una puerta trasera al segundo factor.

Es la unica razon por la que la entrada por correo vive dentro del asistente
de `django-two-factor-auth` y no en una vista aparte. Una vista aparte que
llamara a `login()` habria sido mucho mas corta, y quien tuviera el correo de
otra persona --o acceso a su buzon-- entraria en su cuenta sin tocar el TOTP.

Aqui se comprueba que no: con dispositivo dado de alta, las dos puertas
llevan al mismo sitio, que es la pantalla del segundo factor.
"""

from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from .. import otp_login
from ..login_view import SEND_ACTION

User = get_user_model()

PASSWORD = 'una-contrasena-larga-de-verdad'


class SecondFactorIsNotSkippedTests(TestCase):

    def setUp(self):
        cache.clear()
        self.url = reverse('account:login')
        self.user = User.objects.create_user(
            username='ana',
            email='ana@propensionesabogados.com',
            password=PASSWORD,
            first_name='Ana',
            last_name='Prueba',
        )
        # El nombre importa: `two_factor.utils.default_device()` busca el
        # dispositivo llamado **`default`**, que es el que crea su pantalla de
        # alta. Uno con otro nombre existe, se ve en el admin, y el asistente
        # no lo pide: se entraria con la contrasena a secas creyendo tener
        # segundo factor.
        self.device = TOTPDevice.objects.create(
            user=self.user, name='default', confirmed=True
        )

    def test_con_contrasena_pide_el_segundo_factor(self):
        response = self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'auth-username': 'ana',
            'auth-password': PASSWORD,
        })

        self.assertFalse(response.context['user'].is_authenticated)
        self.assertEqual(response.context['wizard']['steps'].current, 'token')

    def test_con_el_codigo_al_correo_tambien(self):
        """El rodeo por el correo termina en la misma pantalla."""
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

        response = self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            'otp-code': '123456',
        })

        self.assertFalse(response.context['user'].is_authenticated)
        self.assertEqual(response.context['wizard']['steps'].current, 'token')

    def test_sin_dispositivo_no_se_pide_nada_mas(self):
        """
        El segundo factor es **opcional**: quien no lo ha dado de alta entra
        con su contrasena y ya. Si esto dejara de ser cierto, la pantalla
        pediria un codigo de una aplicacion que nadie configuro.
        """
        self.device.delete()

        response = self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'auth-username': 'ana',
            'auth-password': PASSWORD,
        }, follow=True)

        self.assertTrue(response.context['user'].is_authenticated)

    def test_el_admin_manda_a_la_pantalla_de_acceso_del_sitio(self):
        """
        `two_factor` parchea el admin para que su `/admin/login/` redirija
        aqui. Asi no queda una segunda pantalla de acceso --la de Django-- sin
        codigo al correo, sin el freno de `axes` y sin segundo factor.
        """
        response = self.client.get(f'/{settings.ADMIN_URL}login/')

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account:login'), response.url)

    def test_el_alta_del_segundo_factor_esta_donde_la_espera_la_biblioteca(self):
        self.assertEqual(
            reverse('two_factor:setup'), '/accounts/two_factor/setup/'
        )
        self.assertEqual(
            reverse('two_factor:profile'), '/accounts/two_factor/'
        )

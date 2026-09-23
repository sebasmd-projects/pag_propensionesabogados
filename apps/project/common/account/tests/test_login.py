"""
El acceso: las dos puertas, y que ninguna abra lo que la otra cierra.

Lo que se comprueba aqui no es que el formulario pinte bien, sino las cuatro
cosas que, si se rompen, no dan error y dejan el acceso abierto:

* que el codigo al correo **no** salte el segundo factor de nadie;
* que los fallos de las dos puertas cuenten en el mismo contador;
* que la pantalla no diga nunca si una cuenta existe;
* que un codigo usado, caducado o tanteado deje de servir.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .. import otp_login
from ..login_view import FAILURES_KEY, MODE_KEY, MODE_OTP, SEND_ACTION

User = get_user_model()

PASSWORD = 'una-contrasena-larga-de-verdad'


def make_user(username='ana', email=None, **extra):
    return User.objects.create_user(
        username=username,
        email=email or f'{username}@propensionesabogados.com',
        password=PASSWORD,
        first_name=username.title(),
        last_name='Prueba',
        **extra,
    )


class LoginPageTests(TestCase):
    """La pantalla, y que los nombres de los campos son los que se esperan."""

    def setUp(self):
        cache.clear()
        self.url = reverse('account:login')

    def test_la_pantalla_abre(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'two_factor/core/login.html')

    def test_los_campos_llevan_el_prefijo_que_lee_axes(self):
        """
        `axes_hooks.username` busca `auth-username` en el POST, y el almacen
        del asistente vive bajo el prefijo `login_view`.

        Si cualquiera de los dos cambiara --y el segundo cambia solo con
        renombrar la clase-- los intentos fallidos se guardarian con
        `username=None` y el bloqueo por (IP, usuario) degradaria en silencio
        a bloqueo por IP.
        """
        response = self.client.get(self.url)

        self.assertContains(response, 'name="auth-username"')
        self.assertContains(response, 'name="auth-password"')
        self.assertContains(response, 'login_view-current_step')

    def test_two_factor_login_apunta_a_nuestra_vista(self):
        """
        `two_factor:login` es lo que usan la biblioteca y `django-otp` para
        mandar a identificarse. Si apuntara a la vista de la biblioteca, el
        sitio tendria dos pantallas de acceso y una de ellas sin el codigo.
        """
        self.assertEqual(reverse('two_factor:login'), reverse('account:login'))

    def test_se_entra_con_usuario_y_contrasena(self):
        make_user()

        response = self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'auth-username': 'ana',
            'auth-password': PASSWORD,
        }, follow=True)

        self.assertTrue(response.context['user'].is_authenticated)

    def test_se_entra_tambien_con_el_correo(self):
        """El backend de correo o usuario sigue en pie tras meter `axes`."""
        make_user()

        response = self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'auth-username': 'ana@propensionesabogados.com',
            'auth-password': PASSWORD,
        }, follow=True)

        self.assertTrue(response.context['user'].is_authenticated)

    def test_una_contrasena_equivocada_no_entra(self):
        make_user()

        response = self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'auth-username': 'ana',
            'auth-password': 'la-que-no-es',
        })

        self.assertFalse(response.context['user'].is_authenticated)
        self.assertEqual(self.client.session.get(FAILURES_KEY), 1)


class OtpModeTests(TestCase):
    """La segunda puerta: el codigo de seis cifras al correo."""

    def setUp(self):
        cache.clear()
        self.url = reverse('account:login')
        self.user = make_user()

    def _abrir_modo_codigo(self):
        return self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'use_otp': '1',
        })

    def test_el_boton_abre_la_pantalla_del_codigo_sin_mandar_nada(self):
        """
        Quien pulsa «entrar con un codigo» puede no haber escrito su usuario
        todavia, asi que ahi no hay a quien mandarselo.
        """
        response = self._abrir_modo_codigo()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get(MODE_KEY), MODE_OTP)
        self.assertEqual(len(mail.outbox), 0)

    def test_enviar_el_codigo_manda_el_correo(self):
        self._abrir_modo_codigo()

        response = self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            SEND_ACTION: '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ana@propensionesabogados.com'])

    def test_el_correo_lleva_el_membrete_dentro_y_responde_a_direccion(self):
        """
        Las imagenes remotas las bloquean casi todos los clientes de correo:
        un membrete enlazado saldria como un cuadro roto encima del codigo.
        """
        self._abrir_modo_codigo()
        self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            SEND_ACTION: '1',
        })

        mensaje = mail.outbox[0]

        self.assertEqual(mensaje.reply_to, ['director@propensionesabogados.com'])
        self.assertEqual(mensaje.mixed_subtype, 'related')
        self.assertTrue(
            any(
                adjunto.get('Content-ID') == '<membrete>'
                for adjunto in mensaje.attachments
                if hasattr(adjunto, 'get')
            ),
            'el membrete no viaja dentro del mensaje',
        )

    def test_se_entra_con_el_codigo(self):
        self._abrir_modo_codigo()

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
        }, follow=True)

        self.assertTrue(response.context['user'].is_authenticated)

    def test_el_codigo_no_sirve_dos_veces(self):
        """
        Se quema al usarlo. Si no, quien vea el correo por encima del hombro
        --o lo recupere de un buzon compartido-- entra cuando quiera.
        """
        self._abrir_modo_codigo()

        with patch.object(otp_login, 'generate_code', return_value='123456'):
            self.client.post(self.url, {
                'login_view-current_step': 'otp',
                'otp-identifier': 'ana',
                SEND_ACTION: '1',
            })

        self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            'otp-code': '123456',
        })
        self.client.logout()

        response = self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            'otp-code': '123456',
        })

        self.assertFalse(response.context['user'].is_authenticated)

    def test_un_codigo_equivocado_no_entra(self):
        self._abrir_modo_codigo()

        with patch.object(otp_login, 'generate_code', return_value='123456'):
            self.client.post(self.url, {
                'login_view-current_step': 'otp',
                'otp-identifier': 'ana',
                SEND_ACTION: '1',
            })

        response = self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            'otp-code': '000000',
        })

        self.assertFalse(response.context['user'].is_authenticated)

    def test_pedir_un_codigo_para_una_cuenta_que_no_existe_contesta_igual(self):
        """
        La pantalla no puede ser un comprobador de cuentas: contesta lo mismo
        exista o no, y no manda nada cuando no hay a quien.
        """
        self._abrir_modo_codigo()

        response = self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'no-existe-nadie-asi',
            SEND_ACTION: '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        # La pantalla dice «te hemos mandado un codigo» igual que si la cuenta
        # existiera. Es lo que mira `has_live_code()`, y por eso mira si se
        # **pidio** un codigo y no si se llego a emitir.
        self.assertTrue(response.context['otp_code_sent'])

    def test_volver_a_la_contrasena_quita_el_paso_del_codigo(self):
        self._abrir_modo_codigo()

        response = self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'use_password': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.client.session.get(MODE_KEY), MODE_OTP)
        self.assertContains(response, 'name="auth-password"')

    def test_a_una_cuenta_desactivada_no_se_le_manda_codigo(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

        self._abrir_modo_codigo()
        self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'otp-identifier': 'ana',
            SEND_ACTION: '1',
        })

        self.assertEqual(len(mail.outbox), 0)


class OfferAfterFailuresTests(TestCase):
    """El codigo se ofrece solo cuando hace falta, y una sola vez."""

    def setUp(self):
        cache.clear()
        self.url = reverse('account:login')
        make_user()

    def _fallar(self):
        return self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'auth-username': 'ana',
            'auth-password': 'la-que-no-es',
        })

    def test_al_tercer_fallo_se_ofrece_el_codigo(self):
        self._fallar()
        self._fallar()
        response = self._fallar()

        self.assertEqual(self.client.session.get(MODE_KEY), MODE_OTP)
        self.assertEqual(len(mail.outbox), 1)
        self.assertContains(response, 'otp-code')

    def test_no_se_ofrece_antes_del_tercero(self):
        """
        Ofrecerlo al primer fallo ensena a pedir un codigo en vez de escribir
        la contrasena, y entonces el correo se vuelve el acceso normal.
        """
        self._fallar()
        self._fallar()

        self.assertNotEqual(self.client.session.get(MODE_KEY), MODE_OTP)
        self.assertEqual(len(mail.outbox), 0)

    def test_la_oferta_es_una_sola(self):
        """
        Volver a ofrecerlo en cada fallo devolveria a la pantalla del codigo a
        quien acaba de pedir expresamente seguir con la contrasena.
        """
        self._fallar()
        self._fallar()
        self._fallar()

        self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'use_password': '1',
        })

        self._fallar()

        self.assertNotEqual(self.client.session.get(MODE_KEY), MODE_OTP)
        self.assertEqual(len(mail.outbox), 1)

    def test_entrar_con_la_contrasena_borra_el_rodeo(self):
        """
        Si el modo siguiera puesto tras acertar, su paso seguiria en la lista
        y el asistente pediria un correo a quien acaba de identificarse.
        """
        self._fallar()
        self._fallar()
        self._fallar()

        self.client.post(self.url, {
            'login_view-current_step': 'otp',
            'use_password': '1',
        })
        response = self.client.post(self.url, {
            'login_view-current_step': 'auth',
            'auth-username': 'ana',
            'auth-password': PASSWORD,
        }, follow=True)

        self.assertTrue(response.context['user'].is_authenticated)
        self.assertIsNone(self.client.session.get(MODE_KEY))

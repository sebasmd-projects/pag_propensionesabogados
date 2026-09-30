"""
"Olvide mi contrasena" y "Cambiar contrasena".

Lo que se fija aqui es el comportamiento que, si se rompe, no da error y deja la
cuenta a merced de otro:

* que el enlace del correo sea de **un solo uso** y **caduque**;
* que un tercero no pueda saber, por la respuesta, quien tiene cuenta;
* que una clave debil se rechace en los dos formularios;
* que cambiar la clave exija la actual, cuente sus fallos en el mismo freno del
  acceso y no cierre la sesion de quien la cambia.

Los cupos de envio y el comportamiento sin cache estan en `test_account.py`.
"""

import re

from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()

PASSWORD = 'una-contrasena-larga-de-verdad'
NUEVA = 'otra-contrasena-igual-de-larga'
IP = '203.0.113.20'


def make_user(username='ana', **extra):
    return User.objects.create_user(
        username=username,
        email=f'{username}@propensionesabogados.com',
        password=PASSWORD,
        first_name=username.title(),
        last_name='Prueba',
        **extra,
    )


def link_in(message):
    """El enlace de cambio de clave que salio por correo."""
    return re.search(r'https?://\S+\?uidb64=\S+', message.body).group(0)


class ForgotPasswordBase(TestCase):

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        mail.outbox = []

        self.url = reverse('account:forgot_password')
        self.user = make_user()

    def ask(self, identifier='ana@propensionesabogados.com'):
        return self.client.post(
            self.url, {'email_or_username': identifier}, REMOTE_ADDR=IP,
        )

    def open_link(self):
        """Abre el enlace del ultimo correo, como lo haria el navegador."""
        link = link_in(mail.outbox[-1])
        path = link[link.index('/accounts/'):]

        return self.client.get(path, follow=True)


class TheEmailTests(ForgotPasswordBase):

    def test_the_email_goes_out_with_the_link(self):
        self.ask()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ana@propensionesabogados.com'])
        self.assertIn('uidb64=', link_in(mail.outbox[0]))

    def test_it_works_with_the_username_too(self):
        self.ask('ana')

        self.assertEqual(len(mail.outbox), 1)

    def test_it_carries_the_letterhead_and_answers_to_management(self):
        self.ask()
        message = mail.outbox[0]

        self.assertEqual(message.reply_to, ['info@propensionesabogados.com'])
        self.assertEqual(message.mixed_subtype, 'related')
        self.assertIn('cid:membrete', message.alternatives[0][0])
        self.assertTrue(any(
            part.get('Content-ID') == '<membrete>'
            for part in message.attachments if hasattr(part, 'get')
        ))

    def test_it_says_when_the_link_expires(self):
        with override_settings(PASSWORD_RESET_TIMEOUT=45 * 60):
            self.ask()

        self.assertIn('45 minutes', mail.outbox[0].alternatives[0][0])

    def test_the_plain_text_link_is_not_broken_by_html_escaping(self):
        self.ask()

        self.assertNotIn('&amp;', mail.outbox[0].body)
        self.assertIn('&token=', mail.outbox[0].body)

    def test_an_unknown_account_gets_nothing_and_the_answer_is_the_same(self):
        known = self.ask('ana@propensionesabogados.com')
        cache.clear()
        mail.outbox = []
        unknown = self.ask('nadie@propensionesabogados.com')

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.content, unknown.content)

    def test_an_inactive_account_gets_nothing(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

        response = self.ask()

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.status_code, 200)

    def test_an_account_that_only_signs_in_with_a_code_gets_nothing(self):
        """Sin contrasena utilizable no hay clave que restablecer."""
        self.user.set_unusable_password()
        self.user.save()

        self.ask()

        self.assertEqual(len(mail.outbox), 0)


class TheLinkTests(ForgotPasswordBase):

    def test_opening_the_link_shows_the_new_password_form(self):
        self.ask()

        response = self.open_link()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'name="new_password2"')

    def test_the_address_bar_is_left_clean(self):
        """
        El codigo pasa a la sesion y la URL queda limpia: asi no se queda en la
        barra ni viaja en el `Referer` a cualquier recurso externo.
        """
        self.ask()

        response = self.open_link()

        self.assertEqual(response.redirect_chain[-1][0], self.url)
        self.assertNotIn('token', response.wsgi_request.get_full_path())

    def test_a_new_password_is_set_and_the_old_one_stops_working(self):
        self.ask()
        self.open_link()

        response = self.client.post(self.url, {
            'new_password1': NUEVA, 'new_password2': NUEVA,
        })

        self.assertRedirects(
            response, reverse('account:login'), fetch_redirect_response=False)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NUEVA))
        self.assertFalse(self.user.check_password(PASSWORD))

    def test_the_link_only_works_once(self):
        """
        El generador firma con el hash de la clave: en cuanto se cambia, el
        mismo enlace deja de valer. Es lo que hace de esto un codigo de un solo
        uso sin guardar nada en la base.
        """
        self.ask()
        link = link_in(mail.outbox[-1])
        path = link[link.index('/accounts/'):]

        self.client.get(path)
        self.client.post(self.url, {
            'new_password1': NUEVA, 'new_password2': NUEVA,
        })

        # Otro navegador con el mismo enlace.
        otro = self.client_class()
        otro.get(path)
        response = otro.post(self.url, {
            'new_password1': 'una-tercera-clave-larga',
            'new_password2': 'una-tercera-clave-larga',
        }, follow=True)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NUEVA))
        self.assertContains(response, 'invalid or has expired')

    def test_the_link_expires(self):
        self.ask()

        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            response = self.open_link()

        self.assertContains(response, 'invalid or has expired')
        self.assertNotContains(response, 'name="new_password1"')

    def test_a_tampered_token_is_refused(self):
        self.ask()
        link = link_in(mail.outbox[-1])
        path = link[link.index('/accounts/'):]
        path = re.sub(r'token=[^&]+', 'token=abc-0123456789abcdef', path)

        response = self.client.get(path, follow=True)

        self.assertContains(response, 'invalid or has expired')

    def test_a_link_for_another_account_id_is_refused(self):
        self.ask()
        link = link_in(mail.outbox[-1])
        path = link[link.index('/accounts/'):]
        path = re.sub(r'uidb64=[^&]+', 'uidb64=AAAA', path)

        response = self.client.get(path, follow=True)

        self.assertContains(response, 'invalid or has expired')

    def test_a_deactivated_account_cannot_use_a_link_issued_before(self):
        self.ask()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

        response = self.open_link()

        self.assertContains(response, 'invalid or has expired')


class TheNewPasswordIsCheckedTests(ForgotPasswordBase):

    def setUp(self):
        super().setUp()
        self.ask()
        self.open_link()

    def reset(self, first, second=None):
        return self.client.post(self.url, {
            'new_password1': first, 'new_password2': second or first,
        })

    def test_a_weak_password_is_refused(self):
        response = self.reset('12345678')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_a_common_password_is_refused(self):
        response = self.reset('password')

        self.assertTrue(response.context['form'].errors)

    def test_a_short_password_is_refused(self):
        response = self.reset('Ab1!')

        self.assertTrue(response.context['form'].errors)

    def test_the_two_fields_must_match(self):
        response = self.reset(NUEVA, NUEVA + 'x')

        self.assertTrue(response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_a_refused_password_leaves_the_link_usable(self):
        """Equivocarse al teclear no puede quemar el enlace."""
        self.reset('12345678')

        response = self.reset(NUEVA)

        self.assertRedirects(
            response, reverse('account:login'), fetch_redirect_response=False)


class TheSessionIsKeptTests(ForgotPasswordBase):

    def test_someone_signed_in_as_that_account_stays_signed_in(self):
        self.client.force_login(self.user)
        self.ask()
        self.open_link()

        self.client.post(self.url, {
            'new_password1': NUEVA, 'new_password2': NUEVA,
        })

        self.assertIn('_auth_user_id', self.client.session)


# ---------------------------------------------------------------------------
class ChangePasswordTests(TestCase):

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        AccessAttempt.objects.all().delete()

        self.url = reverse('account:change_password')
        self.user = make_user()
        self.client.force_login(self.user)

    def change(self, old=PASSWORD, new=NUEVA, again=None):
        return self.client.post(self.url, {
            'old_password': old,
            'new_password1': new,
            'new_password2': again or new,
        }, REMOTE_ADDR=IP)

    def test_it_needs_a_session(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account:login'), response['Location'])
        self.assertIn('next=', response['Location'])

    def test_the_form_opens(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="old_password"')

    def test_it_changes_the_password(self):
        response = self.change()

        self.assertRedirects(
            response, reverse('core:index'), fetch_redirect_response=False)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NUEVA))

    def test_the_session_survives_the_change(self):
        """
        El hash de la sesion depende de la clave: sin `update_session_auth_hash`
        cambiarla cerraria la sesion de quien acaba de cambiarla.
        """
        self.change()

        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_it_asks_for_the_current_password(self):
        response = self.change(old='no-es-la-actual')

        self.assertEqual(response.status_code, 200)
        self.assertIn('old_password', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_a_weak_new_password_is_refused(self):
        response = self.change(new='12345678')

        self.assertIn('new_password1', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_the_new_password_cannot_be_the_current_one(self):
        response = self.change(new=PASSWORD)

        self.assertIn('new_password1', response.context['form'].errors)

    def test_the_two_new_fields_must_match(self):
        response = self.change(again=NUEVA + 'x')

        self.assertIn('new_password2', response.context['form'].errors)

    def test_a_wrong_current_password_counts_in_the_same_brake_as_the_login(self):
        self.change(old='no-es-la-actual')

        self.assertEqual(
            AccessAttempt.objects.filter(username='ana').count(), 1)

    @override_settings(AXES_FAILURE_LIMIT=2)
    def test_once_locked_even_the_right_password_is_refused(self):
        """
        Sin esto, una sesion robada serviria para adivinar la clave desde aqui
        sin limite: el freno del acceso no lo veria.
        """
        self.change(old='no-es-la-actual')
        self.change(old='tampoco-es-esta')

        self.change()

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_the_user_menu_links_to_it(self):
        response = self.client.get(reverse('core:index'))

        self.assertContains(response, self.url)

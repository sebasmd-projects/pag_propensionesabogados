"""
El rastro de auditoria lleva a quien hizo el cambio.

`AuditlogMiddleware` lee `request.user` una sola vez, al entrar. Cuando estaba
antes que `AuthenticationMiddleware` en `MIDDLEWARE`, `request.user` todavia no
existia y **todo** cambio quedaba en `LogEntry` sin actor. Solo la visibilidad
de las notas lo arreglaba a mano con `set_actor`. Aqui se comprueba con vistas
normales del gestor, sin ningun `set_actor` a mano: crear y editar un cliente.
"""

from io import StringIO

from auditlog.models import LogEntry
from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from ..models import ClientModel
from .test_access import login_as, make_user


class MiddlewareOrderTests(SimpleTestCase):
    """El orden que hace posible el actor, fijado para que no se deshaga."""

    def test_auditlog_va_detras_de_la_autenticacion_y_del_segundo_factor(self):
        mw = settings.MIDDLEWARE
        auth = mw.index('django.contrib.auth.middleware.AuthenticationMiddleware')
        otp = mw.index('django_otp.middleware.OTPMiddleware')
        audit = mw.index('auditlog.middleware.AuditlogMiddleware')

        self.assertLess(auth, otp)
        self.assertLess(otp, audit)


class AuditActorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())

    def setUp(self):
        self.abogada = make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

    def test_crear_un_cliente_deja_el_actor(self):
        respuesta = self.client.post(
            reverse('case_manager:gestor_client_create'),
            {'identification': '16484186', 'full_name': 'Carlos Giraldo',
             'email': '', 'phone': '', 'is_active': 'on'},
        )

        self.assertEqual(respuesta.status_code, 302)
        entry = LogEntry.objects.get_for_object(ClientModel.objects.get()).get()
        self.assertEqual(entry.action, LogEntry.Action.CREATE)
        self.assertEqual(entry.actor, self.abogada)

    def test_editar_un_cliente_deja_el_actor_de_quien_edita(self):
        cliente = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo')
        otra = make_user('otra', gestor=True)
        self.client.logout()
        login_as(self.client, 'otra')

        respuesta = self.client.post(
            reverse('case_manager:gestor_client_update', args=[cliente.pk]),
            {'identification': '16484186', 'full_name': 'Carlos E. Giraldo',
             'email': '', 'phone': '', 'is_active': 'on'},
        )

        self.assertEqual(respuesta.status_code, 302)
        entry = LogEntry.objects.get_for_object(cliente).filter(
            action=LogEntry.Action.UPDATE).get()
        self.assertEqual(entry.actor, otra)

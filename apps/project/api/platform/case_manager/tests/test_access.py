"""
Quien entra al gestor interno.

Lo que esto sustituye cabe en dos lineas de la pantalla anterior::

    const claveAdmin = localStorage.getItem("procrm_admin_password");
    if (u === "propensi" && p === claveAdmin) { ...abrir el panel... }

...con la contrasena por defecto escrita en el HTML, a la vista de
cualquiera que abriera el codigo fuente de la pagina. Un usuario fijo para
todo el despacho, una contrasena publicada, y la comprobacion hecha en la
maquina de quien preguntaba.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from io import StringIO

from ..access import GESTOR_GROUP, can_use_case_manager

User = get_user_model()


def make_user(username, *, staff=False, superuser=False, gestor=False,
              active=True):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@propensionesabogados.com',
        password='una-contrasena-larga-de-verdad',
        first_name=username.title(),
        last_name='Prueba',
        is_staff=staff or superuser,
        is_superuser=superuser,
        is_active=active,
    )
    if gestor:
        user.groups.add(Group.objects.get_or_create(name=GESTOR_GROUP)[0])
    return user


class CanUseCaseManagerTests(TestCase):
    """La pregunta, en un solo sitio."""

    def test_un_visitante_no_puede(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(can_use_case_manager(AnonymousUser()))

    def test_una_cuenta_cualquiera_no_puede(self):
        """
        Registrarse en el sitio no da acceso al despacho. El registro es
        publico; el gestor no.
        """
        self.assertFalse(can_use_case_manager(make_user('cliente')))

    def test_el_grupo_del_gestor_puede(self):
        self.assertTrue(can_use_case_manager(make_user('abogada', gestor=True)))

    def test_un_superusuario_puede(self):
        self.assertTrue(can_use_case_manager(make_user('jefe', superuser=True)))

    def test_una_cuenta_desactivada_no_puede_aunque_tenga_el_grupo(self):
        """
        Dar de baja a alguien es desactivar su cuenta, y eso tiene que bastar:
        nadie se acuerda de quitarle ademas los grupos.
        """
        user = make_user('exempleado', gestor=True, active=False)

        self.assertFalse(can_use_case_manager(user))


class AdminAccessTests(TestCase):
    """La puerta, tal como la ve el navegador."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cls.url = reverse('admin:case_manager_clientmodel_changelist')

    def test_sin_sesion_manda_al_acceso(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_una_cuenta_sin_el_grupo_no_ve_el_gestor(self):
        make_user('cliente', staff=True)
        self.client.login(
            username='cliente', password='una-contrasena-larga-de-verdad'
        )

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_el_grupo_del_gestor_entra(self):
        make_user('abogada', staff=True, gestor=True)
        self.client.login(
            username='abogada', password='una-contrasena-larga-de-verdad'
        )

        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_el_gestor_no_puede_borrar_clientes(self):
        """
        No hay papelera, y un cliente borrado se lleva sus casos y su dinero.
        Para dar de baja esta la vigencia.
        """
        user = make_user('abogada', staff=True, gestor=True)

        from ..admin import ClientAdmin
        from ..models import ClientModel

        admin_class = ClientAdmin(ClientModel, None)
        request = type('R', (), {'user': user})()

        self.assertTrue(admin_class.has_change_permission(request))
        self.assertFalse(admin_class.has_delete_permission(request))

    def test_un_superusuario_si_puede_borrar(self):
        user = make_user('jefe', superuser=True)

        from ..admin import ClientAdmin
        from ..models import ClientModel

        admin_class = ClientAdmin(ClientModel, None)
        request = type('R', (), {'user': user})()

        self.assertTrue(admin_class.has_delete_permission(request))


class PasswordStorageTests(TestCase):
    """
    La contrasena no se guarda, se resume.

    Es lo minimo, y es exactamente lo que no pasaba antes: la contrasena
    administrativa estaba en texto plano en la plantilla y en `localStorage`.
    """

    def test_la_contrasena_no_se_guarda_en_claro(self):
        user = make_user('abogada', gestor=True)
        user.refresh_from_db()

        self.assertNotIn('una-contrasena-larga-de-verdad', user.password)
        self.assertTrue(user.password.startswith('argon2$'))
        self.assertTrue(user.check_password('una-contrasena-larga-de-verdad'))

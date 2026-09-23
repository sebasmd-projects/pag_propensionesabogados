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


def login_as(client, username):
    """
    Deja la sesion abierta como esa cuenta, sin pasar por `authenticate()`.

    `client.login()` ya no vale: desde que el proyecto usa `django-axes`,
    llamar a `authenticate()` **sin la peticion** levanta
    `AxesBackendRequestParameterRequired`. No es una manía de la biblioteca:
    sin peticion no hay IP que contar ni sesion que bloquear, asi que un
    `authenticate()` a secas seria un acceso sin freno, y prefiere reventar a
    dejarlo pasar en silencio. El cliente de pruebas de Django llama asi.

    Lo que hacen estas pruebas es comprobar **permisos**, no el acceso --eso
    tiene las suyas en `apps/project/common/account/tests/`--, asi que lo
    correcto aqui es abrir la sesion directamente y no simular un formulario.

    El backend se nombra a mano porque hay tres configurados y el primero es
    el de `axes`, que es un guardian y no una forma de cargar cuentas.
    """
    user = get_user_model()._default_manager.get(username=username)
    client.force_login(
        user, backend='django.contrib.auth.backends.ModelBackend'
    )
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
        login_as(self.client, 'cliente')

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_el_grupo_del_gestor_entra(self):
        make_user('abogada', staff=True, gestor=True)
        login_as(self.client, 'abogada')

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


class AdminPagesRenderTests(TestCase):
    """
    Que las paginas del gestor en el admin **abran de verdad**.

    Las pruebas de arriba llaman a los metodos de permiso a mano, y eso se les
    escapo: `ModelAdmin.has_add_permission(request)` toma dos argumentos y
    `InlineModelAdmin.has_add_permission(request, obj)` toma tres. Como el
    mixin lo comparten los dos, la firma del `ModelAdmin` rompia el inline del
    dinero en cuanto alguien abria la ficha de un asunto:

        TypeError: CaseManagerAdminMixin.has_add_permission() takes 2
        positional arguments but 3 were given

    Comprobar los metodos sueltos no lo veia; pedir la pagina, si. De ahi que
    estas prueben lo que hace el navegador.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())

        from ..choices import Mandate, Service, Stage
        from ..models import CaseFinanceModel, CaseModel, ClientModel

        cls.client_record = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test'
        )
        cls.case = CaseModel.objects.create(
            client=cls.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )
        CaseFinanceModel.objects.create(
            case=cls.case,
            mandate=Mandate.PAYMENT,
            agreed_fee=6_000_000,
            paid_amount=2_000_000,
        )

    def setUp(self):
        make_user('abogada', staff=True, gestor=True)
        login_as(self.client, 'abogada')

    def test_el_listado_de_clientes_abre(self):
        url = reverse('admin:case_manager_clientmodel_changelist')

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_la_ficha_de_un_cliente_abre(self):
        url = reverse(
            'admin:case_manager_clientmodel_change', args=[self.client_record.pk]
        )

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_el_listado_de_asuntos_abre(self):
        url = reverse('admin:case_manager_casemodel_changelist')

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_anadir_un_asunto_abre(self):
        """Es la pagina que llevaba el inline del dinero y reventaba."""
        url = reverse('admin:case_manager_casemodel_add')

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_la_ficha_de_un_asunto_abre_con_su_inline(self):
        url = reverse('admin:case_manager_casemodel_change', args=[self.case.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # El inline esta de verdad en la pagina, no solo «no revento».
        self.assertContains(response, 'finance')

    def test_un_superusuario_tambien(self):
        self.client.logout()
        make_user('jefe', superuser=True)
        login_as(self.client, 'jefe')

        url = reverse('admin:case_manager_casemodel_change', args=[self.case.pk])

        self.assertEqual(self.client.get(url).status_code, 200)

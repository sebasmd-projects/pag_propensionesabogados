"""
Los enlaces de cuenta en la cabecera.

Van dentro del menu «Plataformas», separados de las plataformas aliadas por
una linea: aquellas llevan fuera del sitio y estos no, y mezclados cuesta ver
cual es cual.

Lo que se prueba es lo que no se ve al mirar la pagina: que «Gestor de
procesos» sale **solo** a quien puede entrar. El enlace no es la puerta --la
puerta esta en la vista, y responde 404-- pero ensenarselo a quien va a
recibir un 404 no ayuda a nadie, y ensenar la direccion del panel a un
visitante cualquiera tampoco.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.project.api.platform.case_manager.access import GESTOR_GROUP

User = get_user_model()

CLAVE = 'una-contrasena-larga-de-verdad'


def make_user(username, *, gestor=False, superuser=False):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@propensionesabogados.com',
        password=CLAVE,
        first_name=username.title(),
        last_name='Prueba',
        is_superuser=superuser,
        is_staff=superuser,
    )
    if gestor:
        user.groups.add(Group.objects.get_or_create(name=GESTOR_GROUP)[0])
    return user


class NavbarAccountLinksTests(TestCase):

    def setUp(self):
        self.url = reverse('core:index')
        self.gestor = reverse('case_manager:gestor_dashboard')
        self.login = reverse('account:login')
        self.logout = reverse('account:logout')

    def entrar(self, user):
        self.client.force_login(
            user, backend='django.contrib.auth.backends.ModelBackend'
        )

    # --- visitante -------------------------------------------------------
    def test_un_visitante_ve_iniciar_sesion_y_no_el_gestor(self):
        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, f'href="{self.login}"')
        self.assertNotContains(respuesta, f'href="{self.gestor}"')
        self.assertNotContains(respuesta, f'href="{self.logout}"')

    # --- con sesion ------------------------------------------------------
    def test_quien_entro_sin_el_grupo_no_ve_el_gestor(self):
        """
        El registro del sitio es publico, asi que cualquiera puede llegar aqui
        con una sesion valida.
        """
        self.entrar(make_user('cliente'))
        respuesta = self.client.get(self.url)

        self.assertNotContains(respuesta, f'href="{self.gestor}"')
        self.assertContains(respuesta, f'href="{self.logout}"')
        self.assertNotContains(respuesta, f'href="{self.login}"')

    def test_el_grupo_del_gestor_si_lo_ve(self):
        self.entrar(make_user('abogada', gestor=True))

        self.assertContains(self.client.get(self.url), f'href="{self.gestor}"')

    def test_un_superusuario_tambien(self):
        self.entrar(make_user('jefe', superuser=True))

        self.assertContains(self.client.get(self.url), f'href="{self.gestor}"')

    def test_una_cuenta_desactivada_no_lo_ve(self):
        user = make_user('exempleado', gestor=True)
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.entrar(user)

        self.assertNotContains(self.client.get(self.url), f'href="{self.gestor}"')

    # --- que la cabecera es la misma en todas ----------------------------
    def test_los_enlaces_salen_en_las_paginas_interiores(self):
        """
        La cabecera es un `include`, asi que esto deberia darse solo. Se
        comprueba porque el portal publico y el gestor extienden plantillas
        distintas, y una de ellas podria dejar de incluirla sin que nadie se
        entere.
        """
        self.entrar(make_user('abogada', gestor=True))

        for ruta in (self.url, reverse('case_manager:public_query')):
            with self.subTest(ruta=ruta):
                self.assertContains(
                    self.client.get(ruta), f'href="{self.gestor}"'
                )

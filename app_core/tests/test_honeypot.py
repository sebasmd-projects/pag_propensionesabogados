"""
Que `django-honeypot` sigue funcionando sobre Django 5.2.

La 1.2.1 declara `django<5.2` como techo de metadatos y el proyecto lo salta
con un override de uv (`pyproject.toml`, `[tool.uv]`). Un override que nadie
comprueba es una suposicion: esto lo convierte en un hecho. Si alguna vez deja
de funcionar, falla aqui y no en el formulario de contacto.
"""

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from honeypot.decorators import check_honeypot
from honeypot.templatetags.honeypot import render_honeypot_field

CAMPO = 'email_confirm_hp'


@override_settings(HONEYPOT_FIELD_NAME=CAMPO)
class HoneypotEnDjango52Tests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

        @check_honeypot
        def vista(request):
            return HttpResponse('pasa')

        self.vista = vista

    def test_el_campo_se_renderiza(self):
        """La etiqueta de plantilla, que es lo que usa el formulario de contacto."""
        html = render_honeypot_field(CAMPO)['fieldname']
        self.assertEqual(html, CAMPO)

    def test_un_envio_con_el_campo_vacio_pasa(self):
        """Una persona no rellena un campo que no ve."""
        peticion = self.factory.post('/', {CAMPO: ''})
        self.assertEqual(self.vista(peticion).status_code, 200)

    def test_un_envio_con_el_campo_relleno_se_rechaza(self):
        """Un robot rellena todo lo que encuentra."""
        peticion = self.factory.post('/', {CAMPO: 'soy-un-robot'})
        self.assertEqual(self.vista(peticion).status_code, 400)

    def test_un_envio_sin_el_campo_se_rechaza(self):
        """Quitar el campo tampoco vale."""
        peticion = self.factory.post('/', {})
        self.assertEqual(self.vista(peticion).status_code, 400)

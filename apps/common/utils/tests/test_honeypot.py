"""
La trampa para robots.

Protege el unico formulario publico que escribe en la base sin sesion --el de
contacto--, asi que si deja de funcionar el sintoma es un buzon lleno, no un
error. Nada avisa. De ahi que se pruebe entera y no solo el caso feliz.

Estas pruebas nacieron comprobando que el paquete `django-honeypot` seguia
funcionando sobre Django 5.2. Ahora comprueban la implementacion propia que lo
sustituye, y por eso cubren tambien lo que el paquete daba por hecho: las tres
formas del decorador, el campo ausente y la exencion.
"""

from django.http import HttpResponse
from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase, override_settings

from ..honeypot import (check_honeypot, honeypot_exempt,
                        verify_honeypot_value)

CAMPO = 'email_confirm_hp'


@override_settings(HONEYPOT_FIELD_NAME=CAMPO)
class CheckHoneypotTests(SimpleTestCase):
    """El decorador, que es lo que protege la vista de contacto."""

    def setUp(self):
        self.factory = RequestFactory()

        @check_honeypot
        def vista(request):
            return HttpResponse('pasa')

        self.vista = vista

    def test_un_envio_con_el_campo_vacio_pasa(self):
        """Una persona no rellena un campo que no ve."""
        peticion = self.factory.post('/', {CAMPO: ''})

        self.assertEqual(self.vista(peticion).status_code, 200)

    def test_un_envio_con_el_campo_relleno_se_rechaza(self):
        """Un robot rellena todo lo que encuentra."""
        peticion = self.factory.post('/', {CAMPO: 'soy-un-robot'})

        self.assertEqual(self.vista(peticion).status_code, 400)

    def test_un_envio_sin_el_campo_se_rechaza(self):
        """
        Quitar el campo antes de enviar tampoco vale.

        Es mas facil que rellenarlo, asi que si la ausencia pasara, la trampa
        no serviria de nada.
        """
        peticion = self.factory.post('/', {})

        self.assertEqual(self.vista(peticion).status_code, 400)

    def test_un_get_no_se_comprueba(self):
        """La trampa es del envio; pedir la pagina no manda ningun campo."""
        self.assertEqual(self.vista(self.factory.get('/')).status_code, 200)

    def test_la_respuesta_de_error_no_explica_la_trampa(self):
        """A quien la dispara no se le cuenta como no dispararla."""
        peticion = self.factory.post('/', {CAMPO: 'robot'})

        cuerpo = self.vista(peticion).content.decode()

        self.assertNotIn(CAMPO, cuerpo)
        self.assertNotIn('honeypot', cuerpo.lower())


@override_settings(HONEYPOT_FIELD_NAME=CAMPO)
class DecoratorFormsTests(SimpleTestCase):
    """
    Las tres formas de escribir el decorador.

    Se prueban porque la vista de contacto usa una y las otras dos son las que
    alguien escribira la proxima vez sin mirar como se hizo la primera.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _vista(self, decorador):
        @decorador
        def vista(request):
            return HttpResponse('pasa')

        return vista

    def test_sin_parentesis(self):
        vista = self._vista(check_honeypot)

        self.assertEqual(
            vista(self.factory.post('/', {CAMPO: ''})).status_code, 200
        )

    def test_con_el_campo_como_posicional(self):
        vista = self._vista(check_honeypot('otro_campo'))

        self.assertEqual(
            vista(self.factory.post('/', {'otro_campo': ''})).status_code, 200
        )
        self.assertEqual(
            vista(self.factory.post('/', {CAMPO: ''})).status_code, 400
        )

    def test_con_el_campo_por_nombre(self):
        vista = self._vista(check_honeypot(field_name='otro_campo'))

        self.assertEqual(
            vista(self.factory.post('/', {'otro_campo': ''})).status_code, 200
        )

    def test_el_decorador_conserva_el_nombre_de_la_vista(self):
        """
        `wraps` no es cosmetico: sin el, el `name` de una ruta y lo que sale
        en una traza pasan a ser `inner`.
        """

        @check_honeypot
        def mi_vista(request):
            return HttpResponse()

        self.assertEqual(mi_vista.__name__, 'mi_vista')


@override_settings(HONEYPOT_FIELD_NAME=CAMPO)
class ExemptTests(SimpleTestCase):
    def test_una_vista_exenta_queda_marcada(self):
        @honeypot_exempt
        def vista(request):
            return HttpResponse()

        self.assertTrue(vista.honeypot_exempt)
        self.assertEqual(vista.__name__, 'vista')


@override_settings(HONEYPOT_FIELD_NAME=CAMPO)
class RenderFieldTests(SimpleTestCase):
    """
    La etiqueta de plantilla, que es lo que pinta el campo en el formulario.

    Se renderiza de verdad, con `{% load honeypot %}`, porque lo que hay que
    comprobar es que esa carga sigue resolviendo despues de haber quitado el
    paquete que antes la daba.
    """

    def _render(self, plantilla, contexto=None):
        return Template(plantilla).render(Context(contexto or {}))

    def test_la_etiqueta_se_carga_con_el_mismo_nombre_de_antes(self):
        html = self._render(
            '{% load honeypot %}{% render_honeypot_field %}'
        )

        self.assertIn(f'name="{CAMPO}"', html)

    def test_se_puede_dar_otro_nombre_de_campo(self):
        html = self._render(
            '{% load honeypot %}{% render_honeypot_field "otro_campo" %}'
        )

        self.assertIn('name="otro_campo"', html)

    def test_el_campo_sale_vacio(self):
        """Si saliera relleno, cada envio legitimo dispararia la trampa."""
        html = self._render('{% load honeypot %}{% render_honeypot_field %}')

        self.assertIn('value=""', html)

    def test_el_campo_no_se_esconde_con_display_none(self):
        """
        Un robot que mire los estilos descartaria un campo con `display:none`
        o `hidden`, y entonces no caeria.
        """
        html = self._render('{% load honeypot %}{% render_honeypot_field %}')

        self.assertNotIn('display:none', html.replace(' ', ''))
        self.assertNotIn('type="hidden"', html)

    def test_lo_que_pinta_es_lo_que_el_decorador_espera(self):
        """
        Las dos mitades tienen que hablar del mismo campo.

        Es la prueba que sostiene el conjunto: si el nombre que se pinta y el
        que se comprueba se separan, cada envio legitimo se rechaza y nadie
        entiende por que.
        """
        html = self._render('{% load honeypot %}{% render_honeypot_field %}')

        self.assertIn(f'name="{CAMPO}"', html)

        peticion = RequestFactory().post('/', {CAMPO: ''})
        self.assertIsNone(verify_honeypot_value(peticion, None))


class SettingsTests(SimpleTestCase):
    """Los ajustes que el paquete permitia y que se conservan."""

    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(HONEYPOT_FIELD_NAME=CAMPO, HONEYPOT_VALUE='esperado')
    def test_honeypot_value_fija_lo_que_tiene_que_llegar(self):
        peticion = self.factory.post('/', {CAMPO: 'esperado'})
        self.assertIsNone(verify_honeypot_value(peticion, None))

        peticion = self.factory.post('/', {CAMPO: ''})
        self.assertIsNotNone(verify_honeypot_value(peticion, None))

    @override_settings(
        HONEYPOT_FIELD_NAME=CAMPO, HONEYPOT_VALUE=lambda: 'calculado'
    )
    def test_honeypot_value_puede_ser_invocable(self):
        peticion = self.factory.post('/', {CAMPO: 'calculado'})

        self.assertIsNone(verify_honeypot_value(peticion, None))

    @override_settings(
        HONEYPOT_FIELD_NAME=CAMPO, HONEYPOT_VERIFIER=lambda value: True
    )
    def test_se_puede_cambiar_el_comprobador(self):
        peticion = self.factory.post('/', {CAMPO: 'lo que sea'})

        self.assertIsNone(verify_honeypot_value(peticion, None))

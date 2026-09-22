"""
El paz y salvo.

Es el unico documento que el portal emite, y antes lo emitia el navegador:
`imprimirPazYSalvoPublico()` abria una ventana y le escribia el documento
concatenando los datos de `localStorage`. Quien editaba ese almacen --o sea,
cualquiera-- se expedia un paz y salvo a nombre de quien quisiera, con el
membrete y la firma escaneada del representante legal dentro.

Estas pruebas son las tres condiciones que ahora hacen falta a la vez.
"""

from django.test import TestCase
from django.urls import reverse

from ..choices import Service, Stage
from ..models import CaseModel, ClientModel


class PazYSalvoAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.query_url = reverse('case_manager:public_query')

        cls.client_record = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo'
        )
        cls.case = CaseModel.objects.create(
            client=cls.client_record,
            service=Service.JUDICIAL,
            stage=Stage.FINISHED,
            subtype='Pensión de invalidez',
            paz_y_salvo_authorized=True,
        )
        cls.url = reverse('case_manager:paz_y_salvo', args=[cls.case.pk])

        otro = ClientModel.objects.create(
            identification='77777777', full_name='Otra Persona'
        )
        cls.otro_case = CaseModel.objects.create(
            client=otro,
            service=Service.CONCILIATION,
            stage=Stage.FINISHED,
            paz_y_salvo_authorized=True,
        )
        cls.otro_url = reverse('case_manager:paz_y_salvo', args=[cls.otro_case.pk])

    def _identificarse(self, identification='16484186', access_key='C4186'):
        return self.client.post(
            self.query_url,
            {'identification': identification, 'access_key': access_key},
        )

    # --- las tres condiciones -------------------------------------------
    def test_sin_identificarse_no_hay_documento(self):
        """
        Saber la direccion no basta.

        Es lo que antes si bastaba: el documento lo armaba el navegador sin
        preguntarle nada a nadie.
        """
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_identificado_y_autorizado_se_expide(self):
        self._identificarse()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Carlos Giraldo')
        self.assertContains(response, 'A PAZ Y SALVO')

    def test_sin_autorizacion_del_despacho_no_se_expide(self):
        """
        El paz y salvo dice que no se debe nada: no lo decide el cliente.
        """
        self._identificarse()
        CaseModel.objects.filter(pk=self.case.pk).update(
            paz_y_salvo_authorized=False
        )

        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_no_se_puede_pedir_el_de_otro(self):
        """
        Identificarse con la clave propia no abre el expediente ajeno, ni
        aunque ese otro caso este autorizado.
        """
        self._identificarse()

        self.assertEqual(self.client.get(self.otro_url).status_code, 404)

    def test_un_caso_sin_vigencia_no_expide(self):
        self._identificarse()
        CaseModel.objects.filter(pk=self.case.pk).update(is_active=False)

        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_fallar_la_clave_no_deja_sesion_abierta(self):
        self.client.post(
            self.query_url,
            {'identification': '16484186', 'access_key': 'X0000'},
        )

        self.assertEqual(self.client.get(self.url).status_code, 404)

    # --- el contenido ----------------------------------------------------
    def test_la_cedula_sale_con_puntos(self):
        """Se guarda sin puntos porque asi se busca; se imprime con ellos."""
        self._identificarse()

        self.assertContains(self.client.get(self.url), '16.484.186')

    def test_el_asunto_es_el_subtipo_y_no_el_radicado(self):
        """
        Regla que venia escrita en el JavaScript original: el paz y salvo
        **no** lleva numero de radicado, solo el tipo de tramite.
        """
        CaseModel.objects.filter(pk=self.case.pk).update(
            case_number='2024-00123-00'
        )
        self._identificarse()

        response = self.client.get(self.url)

        self.assertContains(response, 'Pensión de invalidez')
        self.assertNotContains(response, '2024-00123-00')

    def test_el_enlace_solo_aparece_si_esta_autorizado(self):
        response = self._identificarse()

        self.assertContains(response, 'PAZ Y SALVO')

        CaseModel.objects.filter(pk=self.case.pk).update(
            paz_y_salvo_authorized=False
        )
        response = self._identificarse()

        self.assertNotContains(response, self.url)


class SessionFixationTests(TestCase):
    """
    Identificarse tiene que cambiar el identificador de sesion.

    Sin eso, una sesion preparada de antemano por un tercero seguiria siendo
    valida despues de que el cliente acierte su clave, y esa sesion es la que
    abre el paz y salvo.
    """

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('case_manager:public_query')
        ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo'
        )

    def test_la_sesion_se_renueva_al_acertar(self):
        self.client.get(self.url)
        antes = self.client.session.session_key

        self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'C4186'},
        )

        self.assertNotEqual(self.client.session.session_key, antes)

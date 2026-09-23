"""
La ficha individual y los informes en Word.

Lo que se prueba aqui, por orden de lo que duele si se rompe:

* que la puerta es la misma que la del resto del gestor --un informe con todo
  el dinero del despacho servido a quien pase seria peor que cualquier otra
  fuga de este modulo--;
* que el fichero es un `.docx` **de verdad** y no un HTML con la extension
  cambiada, que es lo que bajaba la pantalla anterior;
* que las cifras del documento son las mismas que las de la pantalla.
"""

import io
import zipfile

from django.test import TestCase
from django.urls import reverse

from ..choices import Mandate, Service, Stage
from ..models import CaseFinanceModel, CaseModel, ClientModel
from .test_access import login_as, make_user

CLAVE = 'una-contrasena-larga-de-verdad'


def texto_del_docx(contenido: bytes) -> str:
    """
    Todo el texto de un `.docx`, para poder buscar dentro.

    Un `.docx` es un zip con XML dentro. Se lee el `document.xml` y se quitan
    las etiquetas; no hace falta mas, porque lo que se comprueba es que una
    cifra este, no como esta maquetada.
    """
    import re

    with zipfile.ZipFile(io.BytesIO(contenido)) as fichero:
        xml = fichero.read('word/document.xml').decode('utf-8')

    return re.sub(r'<[^>]+>', '', xml)


class BaseReportes(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client_record = ClientModel.objects.create(
            identification='16484186',
            full_name='Carlos Emiro Giraldo Lozada',
            email='carlos@example.test',
        )
        cls.case = CaseModel.objects.create(
            client=cls.client_record,
            service=Service.JUDICIAL,
            area='Civil',
            subtype='Responsabilidad civil',
            stage=Stage.IN_PROGRESS,
        )
        CaseFinanceModel.objects.create(
            case=cls.case,
            mandate=Mandate.PAYMENT,
            agreed_fee=8_000_000,
            paid_amount=3_000_000,
        )

        cls.otro = CaseModel.objects.create(
            client=cls.client_record,
            service=Service.CONCILIATION,
            area='Familia',
            stage=Stage.FINAL_STAGE,
        )
        CaseFinanceModel.objects.create(
            case=cls.otro,
            mandate=Mandate.CONTINGENCY,
            contingency_percentage=30,
            contingency_value=9_000_000,
        )


class ClientDetailTests(BaseReportes):
    """La ficha individual, en pantalla."""

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')
        self.url = reverse(
            'case_manager:gestor_client_detail', args=[self.client_record.pk]
        )

    def test_sin_el_grupo_no_se_abre(self):
        self.client.logout()
        make_user('cliente')
        login_as(self.client, 'cliente')

        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_sin_sesion_tampoco(self):
        self.client.logout()

        self.assertNotEqual(self.client.get(self.url).status_code, 200)

    def test_ensena_todos_sus_asuntos_y_no_solo_el_ultimo(self):
        """
        En la pantalla anterior un cliente **era** un asunto. Traducirla
        literalmente habria dejado la ficha ensenando uno solo, que es el
        mismo fallo que ya se corrigio en el portal.
        """
        respuesta = self.client.get(self.url)

        self.assertEqual(len(respuesta.context['cases']), 2)
        self.assertContains(respuesta, 'Responsabilidad civil')
        self.assertContains(respuesta, 'Familia')

    def test_las_cifras_son_las_del_cliente_y_no_las_del_despacho(self):
        """
        `totals()` sobre sus asuntos. Otro cliente con deuda no puede sumar
        aqui, que es lo que pasaria llamando al `totals()` general.
        """
        ajeno = ClientModel.objects.create(
            identification='99999999', full_name='Ajena'
        )
        caso = CaseModel.objects.create(
            client=ajeno, service=Service.JUDICIAL, stage=Stage.IN_PROGRESS
        )
        CaseFinanceModel.objects.create(
            case=caso, mandate=Mandate.PAYMENT, agreed_fee=5_000_000
        )

        totals = self.client.get(self.url).context['totals']

        self.assertEqual(totals['agreed'], 8_000_000)
        self.assertEqual(totals['paid'], 3_000_000)
        self.assertEqual(totals['balance'], 5_000_000)
        self.assertEqual(totals['expectation'], 9_000_000)

    def test_el_listado_de_clientes_enlaza_a_la_ficha(self):
        respuesta = self.client.get(
            reverse('case_manager:gestor_client_list')
        )

        self.assertContains(respuesta, self.url)


class WordReportTests(BaseReportes):
    """Los dos informes descargables."""

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')
        self.ficha = reverse(
            'case_manager:gestor_client_report', args=[self.client_record.pk]
        )
        self.crm = reverse('case_manager:gestor_crm_report')

    # --- la puerta -------------------------------------------------------
    def test_sin_el_grupo_no_se_descargan(self):
        """
        Un informe con todo el dinero del despacho servido a quien pase seria
        peor que cualquier otra fuga de este modulo.
        """
        self.client.logout()
        make_user('cliente')
        login_as(self.client, 'cliente')

        for url in (self.ficha, self.crm):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_sin_sesion_tampoco(self):
        self.client.logout()

        for url in (self.ficha, self.crm):
            with self.subTest(url=url):
                self.assertNotEqual(self.client.get(url).status_code, 200)

    # --- el fichero ------------------------------------------------------
    def test_es_un_docx_de_verdad(self):
        """
        La pantalla anterior bajaba un `.doc` que por dentro era HTML: Word
        avisa de que el formato no coincide con la extension y Google Docs lo
        abre como una pagina web. Un `.docx` es un zip con `word/document.xml`
        dentro; si algun dia esto vuelve a ser HTML, el zip no abre.
        """
        for url in (self.ficha, self.crm):
            with self.subTest(url=url):
                respuesta = self.client.get(url)

                self.assertEqual(respuesta.status_code, 200)
                self.assertIn(
                    'wordprocessingml.document', respuesta['Content-Type']
                )

                with zipfile.ZipFile(io.BytesIO(respuesta.content)) as z:
                    self.assertIn('word/document.xml', z.namelist())

    def test_se_descarga_con_nombre_y_no_se_abre_en_el_navegador(self):
        respuesta = self.client.get(self.ficha)

        self.assertIn('attachment;', respuesta['Content-Disposition'])
        self.assertIn('16484186', respuesta['Content-Disposition'])
        self.assertIn('.docx', respuesta['Content-Disposition'])

    # --- el contenido ----------------------------------------------------
    def test_la_ficha_lleva_al_cliente_y_sus_dos_asuntos(self):
        texto = texto_del_docx(self.client.get(self.ficha).content)

        self.assertIn('Carlos Emiro Giraldo Lozada', texto)
        self.assertIn('16484186', texto)
        self.assertIn('Civil', texto)
        self.assertIn('Familia', texto)

    def test_la_ficha_lleva_las_cifras_con_separador_de_miles(self):
        """
        Un informe que el despacho manda a un cliente no puede decir
        «$8000000»: se lee mal y se teclea peor.
        """
        texto = texto_del_docx(self.client.get(self.ficha).content)

        self.assertIn('$8.000.000', texto)
        self.assertIn('$3.000.000', texto)
        self.assertIn('$5.000.000', texto)

    def test_la_ficha_no_mezcla_clientes(self):
        ClientModel.objects.create(
            identification='99999999', full_name='Ajena Que No Va'
        )
        texto = texto_del_docx(self.client.get(self.ficha).content)

        self.assertNotIn('Ajena Que No Va', texto)

    def test_el_reporte_del_crm_lleva_el_consolidado_y_el_detalle(self):
        texto = texto_del_docx(self.client.get(self.crm).content)

        self.assertIn('Carlos Emiro Giraldo Lozada', texto)
        # pactado 8 000 000, expectativa 9 000 000, proyectado 17 000 000
        self.assertIn('$17.000.000', texto)
        self.assertIn('$9.000.000', texto)

    def test_el_reporte_respeta_la_casilla_de_no_incluir(self):
        """
        «No incluir en panel economico» tiene que valer tambien en el informe;
        si no, una cifra saldria en el Word y no en la pantalla de la que sale.
        """
        oculto = CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            area='Area Oculta',
            stage=Stage.IN_PROGRESS,
        )
        CaseFinanceModel.objects.create(
            case=oculto,
            mandate=Mandate.PAYMENT,
            agreed_fee=1_000_000,
            show_in_dashboard=False,
        )

        texto = texto_del_docx(self.client.get(self.crm).content)

        self.assertNotIn('Area Oculta', texto)

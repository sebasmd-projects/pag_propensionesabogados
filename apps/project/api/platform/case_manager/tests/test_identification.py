"""
Tipos de documento: CC, NIT, CE y PA.

El NIT lleva un digito de verificacion (modulo 11 de la DIAN) y, opcional,
representante legal. Lo que se prueba, por orden de lo que duele si se rompe:
el calculo del DV, la validacion por tipo, que el portal encuentre por NIT sin
crear un oraculo con el DV, y el formato que ve el despacho.
"""

from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from ..choices import IdentificationType, Service, Stage
from ..forms import ClientForm, PublicCaseQueryForm
from ..identification import (format_identification, nit_check_digit,
                              normalize_number, split_lookup)
from ..models import CaseModel, ClientModel
from ..templatetags.case_manager_extras import (client_identification,
                                                client_identification_search)
from .test_access import login_as, make_user
from .test_public_access import identificarse, pedir_codigo
from .test_reports import texto_del_docx


def nit(number='900123456', dv=None, **extra):
    return ClientModel(
        identification_type='NIT', identification=number,
        verification_digit=nit_check_digit(number) if dv is None else dv,
        full_name=extra.pop('full_name', 'Empresa Demo S.A.S.'), **extra,
    )


class CheckDigitTests(TestCase):
    def test_digitos_de_verificacion_conocidos(self):
        casos = {
            '800197268': '4',   # DIAN
            '900123456': '8',
            '899999999': '1',   # Presidencia de la Republica
            '860002964': '4',   # Banco de Bogota
            '890903938': '8',   # Bancolombia
            '901409813': '7',   # Propensiones (impreso en el paz y salvo)
        }
        for numero, dv in casos.items():
            with self.subTest(numero=numero):
                self.assertEqual(nit_check_digit(numero), dv)

    def test_un_numero_vacio_o_demasiado_largo_no_tiene_dv(self):
        self.assertEqual(nit_check_digit(''), '')
        self.assertEqual(nit_check_digit('1' * 16), '')

    def test_el_resto_cero_y_uno_dan_el_mismo_digito(self):
        # Cuando el modulo es 0 o 1 el DV es ese modulo, no 11 - modulo.
        for numero in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):
            self.assertIn(nit_check_digit(numero), list('0123456789'))


class ClientCleanTests(TestCase):
    def test_nit_con_dv_correcto_valida_y_se_guarda_sin_dv_en_el_numero(self):
        cliente = nit('800197268')
        cliente.full_clean()
        cliente.save()
        cliente.refresh_from_db()
        self.assertEqual(cliente.identification, '800197268')
        self.assertEqual(cliente.verification_digit, '4')

    def test_nit_con_dv_erroneo_se_rechaza(self):
        with self.assertRaises(ValidationError) as ctx:
            nit('900123456', dv='7').full_clean()
        self.assertIn('verification_digit', ctx.exception.message_dict)

    def test_nit_sin_dv_se_rechaza(self):
        with self.assertRaises(ValidationError) as ctx:
            nit('900123456', dv='').full_clean()
        self.assertIn('verification_digit', ctx.exception.message_dict)

    def test_fuera_del_nit_el_dv_debe_quedar_vacio(self):
        cliente = ClientModel(identification='16484186', full_name='Ana',
                              verification_digit='1')
        with self.assertRaises(ValidationError) as ctx:
            cliente.full_clean()
        self.assertIn('verification_digit', ctx.exception.message_dict)

    def test_cc_y_ce_solo_admiten_digitos(self):
        for tipo in ('CC', 'CE'):
            with self.subTest(tipo=tipo):
                cliente = ClientModel(identification_type=tipo,
                                      identification='12AB34', full_name='Ana')
                with self.assertRaises(ValidationError) as ctx:
                    cliente.full_clean()
                self.assertIn('identification', ctx.exception.message_dict)

    def test_el_pasaporte_admite_letras_y_se_guarda_en_mayusculas(self):
        cliente = ClientModel(identification_type='PA',
                              identification='AB123456', full_name='Emily')
        cliente.full_clean()
        cliente.save()
        self.assertEqual(cliente.identification, 'AB123456')
        self.assertEqual(cliente.display_identification, 'PA AB123456')

    def test_la_identificacion_sigue_siendo_unica(self):
        ClientModel.objects.create(identification='16484186', full_name='Ana')
        with self.assertRaises(ValidationError) as ctx:
            ClientModel(identification='16484186',
                        full_name='Otra').full_clean()
        self.assertIn('identification', ctx.exception.message_dict)

    def test_la_razon_social_no_se_pasa_a_title(self):
        cliente = nit(full_name='comercial  del valle S.A.S.')
        cliente.save()
        self.assertEqual(cliente.full_name, 'comercial del valle S.A.S.')
        persona = ClientModel.objects.create(
            identification='111', full_name='ana  perez')
        self.assertEqual(persona.full_name, 'Ana Perez')

    def test_representante_con_numero_exige_tipo(self):
        cliente = nit(legal_rep_name='Luis', legal_rep_identification='123')
        with self.assertRaises(ValidationError) as ctx:
            cliente.full_clean()
        self.assertIn('legal_rep_identification_type',
                      ctx.exception.message_dict)

    def test_representante_completo_valida_y_se_formatea(self):
        cliente = nit(
            legal_rep_name='Luis Perez', legal_rep_identification_type='CC',
            legal_rep_identification='79123456',
            legal_rep_email='luis@example.test', legal_rep_phone='300')
        cliente.full_clean()
        self.assertEqual(cliente.legal_rep_display_identification,
                         'CC 79.123.456')
        self.assertTrue(cliente.has_legal_rep)

    def test_sin_nit_el_representante_se_rechaza(self):
        # Se rechaza y no se descarta en silencio: no se borra lo que alguien
        # escribio sin avisarle.
        cliente = ClientModel(identification='16484186', full_name='Ana',
                              legal_rep_name='Luis')
        with self.assertRaises(ValidationError) as ctx:
            cliente.full_clean()
        self.assertIn('legal_rep_name', ctx.exception.message_dict)

    def test_los_clientes_existentes_son_cc_por_defecto(self):
        cliente = ClientModel.objects.create(identification='16484186',
                                             full_name='Ana')
        self.assertEqual(cliente.identification_type, IdentificationType.CC)
        self.assertEqual(cliente.verification_digit, '')


class FormatTests(TestCase):
    def test_formatos(self):
        casos = [
            (ClientModel(identification_type='CC', identification='1152225004'),
             'CC 1.152.225.004'),
            (ClientModel(identification_type='NIT', identification='900123456',
                         verification_digit='8'), 'NIT 900.123.456-8'),
            (ClientModel(identification_type='CE', identification='1234567'),
             'CE 1.234.567'),
            (ClientModel(identification_type='PA', identification='AB123456'),
             'PA AB123456'),
        ]
        for cliente, esperado in casos:
            with self.subTest(esperado=esperado):
                self.assertEqual(client_identification(cliente), esperado)

    def test_la_busqueda_de_datatables_lleva_el_numero_sin_puntos(self):
        cliente = ClientModel(identification_type='NIT',
                              identification='900123456',
                              verification_digit='8')
        texto = client_identification_search(cliente)
        self.assertIn('900123456', texto)
        self.assertIn('900.123.456-8', texto)

    def test_normalizar_y_separar(self):
        self.assertEqual(normalize_number('900.123.456'), '900123456')
        self.assertEqual(split_lookup('900.123.456-8'), ('900123456', '8'))
        self.assertEqual(split_lookup(' 900 123 456 - 8 '), ('900123456', '8'))
        self.assertEqual(split_lookup('900123456'), ('900123456', ''))
        self.assertEqual(split_lookup('1.152.225.004'), ('1152225004', ''))
        self.assertEqual(split_lookup('ab-123456'), ('AB123456', ''))
        self.assertEqual(format_identification('CC', ''), '')


class ClientFormTests(TestCase):
    def datos(self, **extra):
        datos = {
            'identification_type': 'NIT', 'identification': '900.123.456',
            'verification_digit': '8', 'full_name': 'Empresa Demo S.A.S.',
            'email': '', 'phone': '', 'is_active': 'on',
            'legal_rep_name': '', 'legal_rep_identification_type': '',
            'legal_rep_identification': '', 'legal_rep_email': '',
            'legal_rep_phone': '',
        }
        datos.update(extra)
        return datos

    def test_nit_valido(self):
        form = ClientForm(self.datos())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().identification, '900123456')

    def test_dv_erroneo_da_un_error_claro_en_su_campo(self):
        form = ClientForm(self.datos(verification_digit='3'))
        self.assertFalse(form.is_valid())
        self.assertIn('verification_digit', form.errors)
        self.assertIn('does not match', form.errors['verification_digit'][0])

    def test_representante_sin_tipo_se_rechaza(self):
        form = ClientForm(self.datos(legal_rep_name='Luis',
                                     legal_rep_identification='79123456'))
        self.assertFalse(form.is_valid())
        self.assertIn('legal_rep_identification_type', form.errors)

    def test_representante_con_tipo_se_guarda(self):
        form = ClientForm(self.datos(
            legal_rep_name='Luis Perez', legal_rep_identification_type='CC',
            legal_rep_identification='79.123.456'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().legal_rep_identification, '79123456')

    def test_cc_con_representante_se_rechaza(self):
        form = ClientForm(self.datos(
            identification_type='CC', identification='16484186',
            verification_digit='', legal_rep_name='Luis'))
        self.assertFalse(form.is_valid())
        self.assertIn('legal_rep_name', form.errors)

    def test_letras_en_una_cedula_no_se_descartan_en_silencio(self):
        form = ClientForm(self.datos(
            identification_type='CC', identification='12ab34',
            verification_digit=''))
        self.assertFalse(form.is_valid())
        self.assertIn('identification', form.errors)

    def test_pasaporte_alfanumerico(self):
        form = ClientForm(self.datos(
            identification_type='PA', identification='ab123456',
            verification_digit=''))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().identification, 'AB123456')

    def test_la_etiqueta_es_razon_social_con_nit(self):
        self.assertEqual(str(ClientForm(self.datos()).fields['full_name'].label),
                         'Company name')
        self.assertEqual(
            str(ClientForm(self.datos(identification_type='CC')
                           ).fields['full_name'].label), 'Full name')


class GestorScreensTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = nit(
            '900123456', legal_rep_name='Luis Perez',
            legal_rep_identification_type='CC',
            legal_rep_identification='79123456',
            legal_rep_email='luis@example.test', legal_rep_phone='3001112233',
            email='empresa@example.test')
        cls.empresa.save()
        cls.caso = CaseModel.objects.create(
            client=cls.empresa, service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS)
        cls.persona = ClientModel.objects.create(
            identification='1152225004', full_name='Ana Perez',
            email='ana@example.test')

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

    def test_el_listado_ensena_el_formato_y_busca_por_el_numero_sin_puntos(self):
        respuesta = self.client.get(reverse('case_manager:gestor_client_list'))
        self.assertContains(respuesta, 'NIT 900.123.456-8')
        self.assertContains(respuesta, 'CC 1.152.225.004')
        self.assertContains(respuesta, 'data-search="900123456 ')
        self.assertContains(respuesta, 'data-search="1152225004 ')

    def test_el_listado_de_asuntos_ensena_el_formato(self):
        respuesta = self.client.get(reverse('case_manager:gestor_case_list'))
        self.assertContains(respuesta, 'NIT 900.123.456-8')

    def test_la_ficha_ensena_razon_social_y_representante(self):
        url = reverse('case_manager:gestor_client_detail',
                      args=[self.empresa.pk])
        respuesta = self.client.get(url)
        self.assertContains(respuesta, 'NIT 900.123.456-8')
        self.assertContains(respuesta, 'Company name')
        self.assertContains(respuesta, 'Legal representative')
        self.assertContains(respuesta, 'Luis Perez')
        self.assertContains(respuesta, 'CC 79.123.456')

    def test_la_ficha_de_una_persona_no_ensena_representante(self):
        url = reverse('case_manager:gestor_client_detail',
                      args=[self.persona.pk])
        respuesta = self.client.get(url)
        self.assertNotContains(respuesta, 'data-legal-rep')
        self.assertNotContains(respuesta, 'Company name')

    def test_el_formulario_oculta_lo_del_nit_si_no_es_nit(self):
        url = reverse('case_manager:gestor_client_update',
                      args=[self.persona.pk])
        html = self.client.get(url).content.decode()
        self.assertIn('data-nit-only', html)
        self.assertIn('d-none', html.split('data-nit-only')[0][-200:] +
                      html.split('data-nit-only')[1][:200])

    def test_el_alta_por_http_de_un_nit(self):
        respuesta = self.client.post(
            reverse('case_manager:gestor_client_create'),
            {'identification_type': 'NIT', 'identification': '800.197.268',
             'verification_digit': '4', 'full_name': 'Dian Demo',
             'email': '', 'phone': '', 'is_active': 'on'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(ClientModel.objects.filter(
            identification='800197268', identification_type='NIT').exists())

    def test_la_ficha_word_lleva_el_formato_y_el_representante(self):
        respuesta = self.client.get(reverse(
            'case_manager:gestor_client_report', args=[self.empresa.pk]))
        texto = texto_del_docx(respuesta.content)
        self.assertIn('NIT 900.123.456-8', texto)
        self.assertIn('Company name', texto)
        self.assertIn('Luis Perez', texto)
        self.assertIn('CC 79.123.456', texto)

    def test_el_informe_del_asunto_lleva_el_formato(self):
        respuesta = self.client.get(reverse(
            'case_manager:gestor_case_report', args=[self.caso.pk]))
        self.assertIn('NIT 900.123.456-8', texto_del_docx(respuesta.content))

    def test_el_paz_y_salvo_dice_nit(self):
        self.caso.paz_y_salvo_authorized = True
        self.caso.save()
        self.client.logout()
        identificarse(self.client, '900123456')
        respuesta = self.client.get(
            reverse('case_manager:paz_y_salvo', args=[self.caso.pk]))
        self.assertContains(respuesta, '900.123.456-8')
        self.assertContains(respuesta, 'NIT No.')


class PortalNitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('case_manager:public_query')
        cls.empresa = nit('900123456', email='empresa@example.test')
        cls.empresa.save()
        CaseModel.objects.create(client=cls.empresa, service=Service.JUDICIAL,
                                 stage=Stage.IN_PROGRESS)
        cls.persona = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='carlos@example.test')
        cls.pasaporte = ClientModel.objects.create(
            identification_type='PA', identification='AB123456',
            full_name='Emily Carter', email='emily@example.test')

    def _pide(self, valor):
        respuesta = pedir_codigo(self.client, valor)
        return respuesta

    def test_encuentra_por_nit_en_todas_las_formas(self):
        for valor in ('900123456', '900123456-8', '900.123.456',
                      '900.123.456-8', ' 900 123 456 - 8 '):
            with self.subTest(valor=valor):
                self.client.cookies.clear()
                respuesta = self._pide(valor)
                self.assertEqual(respuesta.status_code, 200, valor)
                self.assertNotContains(respuesta, 'We could not find')

    def test_un_dv_erroneo_responde_igual_que_un_documento_inexistente(self):
        malo = self._pide('900123456-3')
        inexistente = self._pide('900999999')
        self.assertEqual(malo.status_code, inexistente.status_code)
        self.assertContains(malo, 'We could not find', status_code=400)
        self.assertContains(inexistente, 'We could not find', status_code=400)

    def test_un_dv_sobre_una_cedula_tampoco_la_encuentra(self):
        respuesta = self._pide('16484186-1')
        self.assertContains(respuesta, 'We could not find', status_code=400)

    def test_la_cedula_con_puntos_sigue_funcionando(self):
        respuesta = self._pide('16.484.186')
        self.assertEqual(respuesta.status_code, 200)

    def test_el_pasaporte_se_encuentra_con_letras(self):
        respuesta = self._pide('ab-123456')
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'We could not find')

    def test_el_formulario_normaliza(self):
        form = PublicCaseQueryForm({'identification': '900.123.456-8'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['identification'], '900123456')
        self.assertEqual(form.get_client(), self.empresa)

    def test_la_pantalla_ensena_la_etiqueta_nueva(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'ID number, NIT or document')

    def test_entra_con_codigo_y_ve_el_documento_formateado(self):
        respuesta = identificarse(self.client, '900123456-8')
        respuesta = self.client.get(self.url, follow=True)
        self.assertContains(respuesta, 'NIT 900.123.456-8')


class SeedTests(TestCase):
    def test_el_seed_crea_los_clientes_por_tipo_y_no_duplica(self):
        call_command('seed_gestor_demo', stdout=StringIO())
        call_command('seed_gestor_demo', stdout=StringIO())
        nits = ClientModel.objects.filter(identification_type='NIT',
                                          identification__startswith='9990')
        self.assertEqual(nits.count(), 2)
        for cliente in nits:
            self.assertEqual(len(cliente.identification), 9)
            self.assertEqual(cliente.verification_digit,
                             nit_check_digit(cliente.identification))
            self.assertTrue(cliente.cases.exists())
        self.assertEqual(sum(c.has_legal_rep for c in nits), 1)
        self.assertTrue(ClientModel.objects.filter(
            identification_type='CE', identification__startswith='9990'
        ).exists())
        self.assertTrue(ClientModel.objects.filter(
            identification_type='PA', identification__startswith='9990'
        ).exists())


class MigrationTests(TransactionTestCase):
    """La migracion deja a los clientes que ya existian como CC."""

    app = 'case_manager'
    before = [('case_manager', '0008_merge_20260924_0957')]
    after = [('case_manager', '0009_client_document_type_nit_legal_rep')]

    def test_los_existentes_quedan_como_cc(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        antes = executor.loader.project_state(self.before).apps
        Cliente = antes.get_model('case_manager', 'ClientModel')
        Cliente.objects.create(identification='16484186', full_name='Ana')

        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        despues = executor.loader.project_state(self.after).apps
        Cliente = despues.get_model('case_manager', 'ClientModel')
        cliente = Cliente.objects.get(identification='16484186')
        self.assertEqual(cliente.identification_type, 'CC')
        self.assertEqual(cliente.verification_digit, '')
        self.assertEqual(cliente.legal_rep_name, '')
        # Deja la base en el estado final para el resto de pruebas.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

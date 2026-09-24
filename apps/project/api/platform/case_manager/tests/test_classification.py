"""Regresiones del formato st/st2 exportado y de los selectores del gestor."""
import json
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.forms.models import model_to_dict
from django.test import TestCase

from ..choices import Service
from ..forms import CaseForm
from ..models import CaseFinanceModel, CaseModel, ClientModel


class ClassificationTests(TestCase):
    def test_imported_judicial_cases_can_be_edited(self):
        records = {
            '10001': {'n': 'Cliente pensional', 's': Service.JUDICIAL,
                      'a': 'Pensional / Seguridad Social', 't': '', 'st': 'Laboral',
                      'st2': 'Pensión de vejez', 'e': 3, 'i': 'Primera instancia',
                      'r': '63001310500120230010200', 'd': 'Juzgado del Circuito',
                      'cp': 'Armenia', 'fi': '2024-02', 'mm': 'Cuota litis',
                      'pl': 0, 'vl': 15000000, 'pr': 15000000, 'estadoPagoV29': 'PAGADO'},
            '10002': {'n': 'Cliente consumidor', 's': Service.JUDICIAL,
                      'st': 'Superintendencias', 'st2': 'Protección al consumidor',
                      'e': 3, 'i': 'Primera instancia', 'r': '26-277458-9',
                      'd': 'Superintendencia', 'cp': 'Bogota', 'fi': '2026-03',
                      'mm': 'Cuota litis', 'pl': 20, 'vl': 13000000},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cases.json'
            path.write_text(json.dumps(records))
            call_command('import_propdemo', str(path), stdout=StringIO())
        for case in CaseModel.objects.all():
            with self.subTest(subtype=case.subtype):
                case.full_clean()
                form = CaseForm(data=model_to_dict(case), instance=case)
                self.assertTrue(form.is_valid(), form.errors)
                for name in ('subtype', 'second_subtype', 'instance'):
                    self.assertIsInstance(form.fields[name].widget, forms.Select)
                form.save()
                case.refresh_from_db()
                self.assertEqual(case.second_subtype, records[case.client.identification]['st2'])
        fixed = CaseFinanceModel.objects.get(contingency_percentage=0)
        fixed.full_clean()
        self.assertEqual(fixed.start_date, date(2024, 2, 1))
        self.assertEqual(fixed.paid, 15000000)
        self.assertEqual(fixed.balance, 0)
        self.assertFalse(CaseFinanceModel.objects.debtors().exists())
        totals = CaseFinanceModel.objects.totals()
        self.assertEqual(totals['balance'], 0)
        self.assertEqual(totals['paid'], 15000000)
        self.assertEqual(totals['expectation'], 13000000)

    def setUp(self):
        self.customer = ClientModel.objects.create(identification='20000', full_name='Cliente')

    def data(self, **kwargs):
        return {'client': self.customer.pk, 'service': Service.JUDICIAL,
                'stage': 0, **kwargs}

    def test_dependent_options_use_posted_parents(self):
        form = CaseForm(data=self.data(subtype='Superintendencias', second_subtype='Protección al consumidor'))
        self.assertTrue(form.is_valid(), form.errors)
        bad = CaseForm(data=self.data(subtype='Laboral', second_subtype='Protección al consumidor'))
        self.assertFalse(bad.is_valid())
        self.assertIn('second_subtype', bad.errors)

    def test_server_rejects_forged_subtype(self):
        form = CaseForm(data=self.data(area='Civil', subtype='<inventado>'))
        self.assertFalse(form.is_valid())
        self.assertIn('subtype', form.errors)

    def test_other_requires_description_and_round_trips(self):
        # El tercer nivel solo existe dentro de una rama: sin subtipo elegido
        # no hay «Otro» que escoger, porque no hay nada de lo que ser otro.
        padres = {'second_subtype': {'subtype': 'Laboral'}}
        for name in ('service', 'procedure', 'area', 'subtype', 'second_subtype'):
            with self.subTest(field=name):
                data = self.data(**{name: 'Otro'}, **padres.get(name, {}))
                form = CaseForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn(name + '_other', form.errors)
                data[name + '_other'] = 'Especialidad particular'
                form = CaseForm(data=data)
                self.assertTrue(form.is_valid(), form.errors)
                case = form.save()
                case.refresh_from_db()
                self.assertEqual(getattr(case, name + '_display'), 'Especialidad particular')

    def test_direct_area_subtype_remains_valid(self):
        form = CaseForm(data=self.data(area='Civil', subtype='Responsabilidad civil'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_model_rejects_wrong_second_level(self):
        case = CaseModel(client=self.customer, service=Service.JUDICIAL,
                         subtype='Laboral', second_subtype='Protección al consumidor')
        with self.assertRaises(ValidationError):
            case.full_clean()

    def test_legacy_free_second_level_is_preserved_but_not_forgeable(self):
        case = CaseModel.objects.create(
            client=self.customer, service=Service.JUDICIAL, area='Civil',
            subtype='Responsabilidad civil', second_subtype='Detalle histórico',
        )
        data = model_to_dict(case)
        form = CaseForm(data=data, instance=case)
        self.assertTrue(form.is_valid(), form.errors)
        data['second_subtype'] = 'Texto ajeno al catálogo'
        self.assertFalse(CaseForm(data=data, instance=case).is_valid())

    def test_partial_fixed_payment_matches_aggregates(self):
        case = CaseModel.objects.create(client=self.customer, service=Service.JUDICIAL)
        finance = CaseFinanceModel.objects.create(
            case=case, mandate='Cuota litis', contingency_percentage=0,
            contingency_value=1000000, paid_amount=250000,
        )
        finance.full_clean()
        self.assertEqual(finance.balance, 750000)
        self.assertTrue(CaseFinanceModel.objects.debtors().filter(pk=finance.pk).exists())
        self.assertEqual(CaseFinanceModel.objects.totals()['balance'], finance.balance)
        finance.contingency_percentage = 20
        with self.assertRaises(ValidationError) as error:
            finance.full_clean()
        self.assertIn('paid_amount', error.exception.message_dict)


class DetailRowsTests(TestCase):
    """
    El bloque de detalle de la ficha publica.

    Colgaba del tipo de tramite, y los expedientes reales vienen **sin** tipo
    de tramite: la pantalla dejo de pedirlo cuando el subtipo paso a colgar
    del servicio. El resultado era que el despacho y la ciudad se guardaban y
    el cliente no los veia; un asunto con «Juzgado del Circuito» y «Armenia»
    dentro se le ensenaba sin ninguno de los dos.
    """

    def setUp(self):
        self.client_record = ClientModel.objects.create(
            identification='13883170',
            full_name='Jose Arcesio Lopez Arias',
            email='jose@example.test',
        )

    def _caso(self, **extra):
        datos = {
            'client': self.client_record,
            'service': Service.JUDICIAL,
            'stage': 3,
            'subtype': 'Laboral',
            'second_subtype': 'Pensión de vejez',
        }
        datos.update(extra)
        return CaseModel.objects.create(**datos)

    def _etiquetas(self, caso):
        return [str(etiqueta) for etiqueta, _valor in caso.detail_rows]

    def test_sin_tipo_de_tramite_el_despacho_y_la_ciudad_salen_igual(self):
        caso = self._caso(
            procedure='',
            court='Juzgado del Circuito',
            city='Armenia',
        )

        self.assertEqual(
            caso.detail_rows,
            [('COURT', 'Juzgado del Circuito'), ('CITY OF THE PROCESS', 'Armenia')],
        )

    def test_el_bloque_administrativo_tampoco_lo_necesita(self):
        caso = self._caso(
            procedure='',
            sector='Público',
            entity='Colpensiones',
            administrative_city='Bogotá',
        )

        self.assertIn('ENTITY / COMPANY', self._etiquetas(caso))
        self.assertIn('NATURE', self._etiquetas(caso))

    def test_solo_sale_lo_que_tiene_contenido(self):
        """
        Los tres bloques se recorren enteros, pero un asunto no llena mas de
        uno: lo vacio no deja filas en blanco en la ficha.
        """
        caso = self._caso(procedure='', court='Juzgado del Circuito')

        self.assertEqual(self._etiquetas(caso), ['COURT'])

    def test_un_asunto_sin_ningun_detalle_no_pinta_el_bloque(self):
        self.assertEqual(self._caso(procedure='').detail_rows, [])

    def test_el_despacho_llega_al_portal_del_cliente(self):
        """
        La prueba de arriba mira el modelo; esta mira lo que el cliente lee.
        """
        from unittest.mock import patch

        from django.urls import reverse

        from .. import portal_otp

        self._caso(procedure='', court='Juzgado del Circuito', city='Armenia')
        url = reverse('case_manager:public_query')

        with patch.object(portal_otp, 'generate_code', return_value='123456'):
            self.client.post(url, {'identification': '13883170'})

        respuesta = self.client.post(url, {'code': '123456'})

        self.assertContains(respuesta, 'Juzgado del Circuito')
        self.assertContains(respuesta, 'Armenia')


class ArbolAprobadoTests(TestCase):
    """
    El arbol del HTML entregado, tal cual: servicio -> subtipo -> proceso.

    Lo que se comprueba aqui no es que las listas tengan tal o cual palabra,
    sino la propiedad que hacia fallar el formulario: que cada desplegable
    ofrezca **solo** lo que cuelga de la rama elegida. Mientras el subtipo
    judicial mezclaba las jurisdicciones con los subtipos de todas las areas,
    un expediente bien clasificado podia recibir «este subtipo no
    corresponde», que es exactamente lo que se reporto.
    """

    def setUp(self):
        self.cliente = ClientModel.objects.create(
            identification='30000', full_name='Cliente'
        )

    def datos(self, **kwargs):
        return {'client': self.cliente.pk, 'service': Service.JUDICIAL,
                'stage': 0, **kwargs}

    def test_el_subtipo_judicial_solo_trae_las_areas_del_arbol(self):
        from ..choices import subtypes_for

        valores = subtypes_for(Service.JUDICIAL)

        self.assertEqual(
            [v for v in valores if v != 'Otro'],
            ['Civil', 'Contencioso administrativo', 'Familia', 'Laboral',
             'Penal', 'Superintendencias'],
        )

    def test_el_tercer_nivel_solo_trae_los_procesos_de_su_area(self):
        from ..choices import second_subtypes_for

        penales = second_subtypes_for(Service.JUDICIAL, 'Penal')

        self.assertIn('Defensa penal', penales)
        self.assertNotIn('Ejecutivo laboral', penales)
        self.assertNotIn('Protección al consumidor', penales)

    def test_una_rama_sin_tercer_nivel_no_ofrece_ninguno(self):
        """
        Un «Recurso de reposición» no se subdivide.

        Devolver `('Otro',)` seria ensenar un desplegable con una sola opcion
        que no significa nada; vacio es lo que le dice al formulario que
        esconda el campo entero.
        """
        from ..choices import second_subtypes_for

        self.assertEqual(
            second_subtypes_for('Administrativo', 'Recurso de reposición'), ()
        )

    def test_los_desplegables_salen_en_orden_alfabetico(self):
        from ..choices import Area, Court, Procedure, Service as Serv
        from ..choices import alphabetical

        for grupo in (Serv, Procedure, Area, Court):
            with self.subTest(grupo=grupo.__name__):
                self.assertEqual(
                    list(grupo.values), list(alphabetical(grupo.values))
                )

    def test_los_juzgados_administrativos_estan_en_la_lista(self):
        """
        Faltaban las dos primeras instancias de lo contencioso administrativo.

        Sin ellas, una nulidad y restablecimiento del derecho --que esta en el
        arbol-- no tenia despacho que escoger: la lista saltaba del juzgado
        del circuito al Consejo de Estado.
        """
        from ..choices import Court

        self.assertIn('Juzgado Administrativo', Court.values)
        self.assertIn('Tribunal Administrativo', Court.values)

    def test_los_dos_expedientes_reales_siguen_siendo_validos(self):
        """
        Los dos que hay en produccion, con su clasificacion exportada.

        Son `st`/`st2` del fichero entregado: uno laboral con pension de vejez
        y otro de superintendencias con proteccion al consumidor. Si el arbol
        nuevo los rechazara, el gestor no podria volver a guardarlos.
        """
        casos = (
            {'area': 'Pensional / Seguridad Social', 'subtype': 'Laboral',
             'second_subtype': 'Pensión de vejez',
             'court': 'Juzgado del Circuito'},
            {'subtype': 'Superintendencias',
             'second_subtype': 'Protección al consumidor',
             'court': 'Superintendencia'},
        )

        for caso in casos:
            with self.subTest(subtype=caso['subtype']):
                form = CaseForm(data=self.datos(instance='Primera instancia', **caso))
                self.assertTrue(form.is_valid(), form.errors)

    def test_el_formulario_no_ofrece_un_proceso_de_otra_area(self):
        form = CaseForm(
            data=self.datos(subtype='Penal', second_subtype='Ejecutivo laboral')
        )

        self.assertFalse(form.is_valid())
        self.assertIn('second_subtype', form.errors)


class TiempoTranscurridoTests(TestCase):
    """Cuanto lleva abierto el asunto, que es lo que se pregunta por telefono."""

    def test_el_portal_ensena_el_tiempo_desde_el_inicio(self):
        from unittest.mock import patch

        from django.urls import reverse

        from .. import portal_otp

        cliente = ClientModel.objects.create(
            identification='40000', full_name='Cliente', email='c@example.com'
        )
        caso = CaseModel.objects.create(
            client=cliente, service=Service.JUDICIAL, stage=3
        )
        CaseFinanceModel.objects.create(
            case=caso, start_date=date(2024, 2, 1), mandate='Cuota litis',
            contingency_percentage=0, contingency_value=15000000,
        )
        url = reverse('case_manager:public_query')

        with patch.object(portal_otp, 'generate_code', return_value='123456'):
            self.client.post(url, {'identification': '40000'})

        respuesta = self.client.post(url, {'code': '123456'})

        self.assertContains(respuesta, '02/2024')
        self.assertContains(respuesta, caso.public_elapsed)

    def test_un_asunto_sin_bloque_economico_no_inventa_una_fecha(self):
        cliente = ClientModel.objects.create(
            identification='40001', full_name='Cliente'
        )
        caso = CaseModel.objects.create(client=cliente, service=Service.JUDICIAL)

        self.assertIsNone(caso.public_start)
        self.assertEqual(caso.public_elapsed, '—')

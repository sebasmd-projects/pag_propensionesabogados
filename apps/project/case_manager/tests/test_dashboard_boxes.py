"""
Los cuadros del panel: un asunto no puede quedar sin categoria.

Lo que se protege es la promesa del panel: **todo asunto sale en alguna
tabla**. Antes solo salian deudores y expectativas, y los pagados, el ad
honorem, la curaduria, los inactivos o los marcados «No incluir en panel»
estaban en la base pero no en la pantalla, sin que nada dijera que faltaban.
"""

import itertools
from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from ..choices import Mandate, Service, Stage
from ..dashboard_boxes import build_boxes
from ..models import CaseFinanceModel, CaseModel, ClientModel
from .test_access import login_as, make_user

_counter = itertools.count(1)


def make_case(name, mandate=None, *, active=True, show=True, authorized=False,
              **finance):
    """Un cliente, un asunto y (si hay `mandate`) su bloque economico."""
    number = next(_counter)
    client = ClientModel.objects.create(
        identification=str(70_000_000 + number), full_name=name,
        email=f'cliente{number}@example.test',
    )
    case = CaseModel.objects.create(
        client=client, service=Service.JUDICIAL, stage=Stage.IN_PROGRESS,
        is_active=active, paz_y_salvo_authorized=authorized,
    )
    if mandate is not None:
        CaseFinanceModel.objects.create(
            case=case, mandate=mandate, show_in_dashboard=show, **finance
        )
    return case


def names(box):
    return sorted(row['cells'][0]['text'].lower() for row in box.rows)


def boxes():
    return {box.key: box for box in build_boxes()}


class DashboardBoxContentTests(TestCase):
    """Cada cuadro lista los asuntos correctos con datos fabricados."""

    @classmethod
    def setUpTestData(cls):
        P, C = Mandate.PAYMENT, Mandate.CONTINGENCY
        # Pagados por completo (con y sin paz y salvo autorizado).
        make_case('Pagado exacto', P, agreed_fee=5_000_000,
                  paid_amount=5_000_000, authorized=True)
        make_case('Pagado de mas', P, agreed_fee=5_000_000,
                  paid_amount=6_000_000)
        make_case('Fijo cubierto', C, contingency_percentage=0,
                  contingency_value=3_000_000, paid_amount=3_000_000)
        # Deudores y expectativas: NO salen en los cuadros nuevos.
        make_case('Debe', P, agreed_fee=5_000_000, paid_amount=1_000_000)
        make_case('Fijo debe', C, contingency_percentage=0,
                  contingency_value=2_000_000, paid_amount=0)
        make_case('Expectativa', C, contingency_percentage=30,
                  contingency_value=9_000_000)
        # Sin dinero.
        make_case('Gratis', Mandate.PRO_BONO)
        make_case('Curador', Mandate.GUARDIANSHIP)
        # Cuota litis al 0 % sin valor todavia.
        make_case('Fijo sin valor', C, contingency_percentage=0)
        # Con modalidad y sin cifras.
        make_case('Pago sin cifras', P)
        make_case('Litis sin valor', C, contingency_percentage=25)
        # Fuera del panel.
        make_case('Oculto', P, show=False, agreed_fee=1_000_000)
        make_case('Inactivo', P, active=False, agreed_fee=1_000_000)
        make_case('Inactivo y oculto', P, active=False, show=False,
                  agreed_fee=1_000_000)
        make_case('Inactivo sin bloque', None, active=False)
        make_case('Sin bloque', None)

    def test_pagados_por_completo(self):
        self.assertEqual(
            names(boxes()['paid_in_full']),
            ['fijo cubierto', 'pagado de mas', 'pagado exacto'],
        )

    def test_pagados_dicen_si_el_paz_y_salvo_esta_autorizado(self):
        rows = {
            row['cells'][0]['text'].lower(): row['cells'][-1]['text']
            for row in boxes()['paid_in_full'].rows
        }
        self.assertEqual(rows['pagado exacto'], 'Authorized')
        self.assertEqual(rows['pagado de mas'], 'Not authorized')

    def test_ad_honorem_y_curaduria(self):
        self.assertEqual(names(boxes()['pro_bono']), ['gratis'])
        self.assertEqual(names(boxes()['guardianship']), ['curador'])

    def test_cuota_litis_al_cero_sin_deuda(self):
        """Las que deben ya estan en deudores; aqui las que no deben nada."""
        box = boxes()['fixed_contingency']
        self.assertEqual(names(box), ['fijo cubierto', 'fijo sin valor'])
        # Justificado: esta tambien sale en «Pagados», y el cuadro dice su estado.
        estado = {r['cells'][0]['text'].lower(): r['cells'][-1]['text']
                  for r in box.rows}
        self.assertEqual(estado['fijo cubierto'], 'Covered')
        self.assertEqual(estado['fijo sin valor'], 'No value set')
        self.assertNotIn(
            'Fijo debe',
            {f.case.client.full_name
             for f in CaseFinanceModel.objects.fixed_contingency()
             .select_related('case__client')},
        )

    def test_modalidad_sin_cifras(self):
        self.assertEqual(
            names(boxes()['unclassified']),
            ['litis sin valor', 'pago sin cifras'],
        )

    def test_marcados_no_incluir_en_panel(self):
        """Solo los vigentes: un inactivo va al cuadro de inactivos."""
        self.assertEqual(names(boxes()['hidden']), ['oculto'])

    def test_inactivos_con_o_sin_bloque_economico(self):
        self.assertEqual(
            names(boxes()['inactive']),
            ['inactivo', 'inactivo sin bloque', 'inactivo y oculto'],
        )

    def test_vigentes_sin_bloque_economico(self):
        self.assertEqual(names(boxes()['no_finance']), ['sin bloque'])

    def test_los_cuadros_viejos_siguen_como_estaban(self):
        debtors = {f.case.client.full_name.lower() for f in
                   CaseFinanceModel.objects.debtors().select_related('case__client')}
        self.assertEqual(debtors, {'debe', 'fijo debe'})
        expectations = {
            f.case.client.full_name.lower() for f in
            CaseFinanceModel.objects.expectations().select_related('case__client')
        }
        self.assertEqual(expectations, {'expectativa'})

    def test_cada_fila_enlaza_al_asunto(self):
        for box in build_boxes():
            for row in box.rows:
                url = row['cells'][0]['url']
                self.assertEqual(
                    url,
                    reverse('case_manager:gestor_case_update',
                            args=[row['case_id']]),
                )


class DashboardCoverageTests(TestCase):
    """Ningun asunto se queda sin categoria."""

    def covered(self):
        from ..models import CaseFinanceModel
        ids = set()
        for box in build_boxes():
            ids |= box.case_ids
        ids |= set(CaseFinanceModel.objects.debtors()
                   .values_list('case_id', flat=True))
        ids |= set(CaseFinanceModel.objects.expectations()
                   .values_list('case_id', flat=True))
        return ids

    def test_con_los_datos_de_prueba_ningun_asunto_queda_sin_categoria(self):
        call_command('seed_gestor_demo', stdout=StringIO())
        self.assertGreater(CaseModel.objects.count(), 30)

        missing = CaseModel.objects.exclude(pk__in=self.covered())

        self.assertEqual(
            list(missing.values_list('client__full_name', flat=True)), []
        )

    def test_toda_combinacion_de_modalidad_y_cifras_cae_en_una_categoria(self):
        """
        La malla completa: modalidad x porcentaje x cifras x pagado x
        (en panel / oculto) x (vigente / inactivo), mas los sin bloque.
        """
        cases, finances = [], []
        combos = itertools.product(
            Mandate.values, (0, 30), (0, 5_000_000), (0, 5_000_000),
            (0, 3_000_000, 5_000_000, 7_000_000), (True, False), (True, False),
        )
        for index, (mandate, pct, fee, value, paid, show, active) in enumerate(combos):
            client = ClientModel.objects.create(
                identification=str(80_000_000 + index),
                full_name=f'Malla {index}',
            )
            case = CaseModel.objects.create(
                client=client, service=Service.JUDICIAL, is_active=active,
            )
            cases.append(case)
            finances.append(CaseFinanceModel(
                case=case, mandate=mandate, contingency_percentage=pct,
                agreed_fee=fee, contingency_value=value, paid_amount=paid,
                show_in_dashboard=show,
            ))
        CaseFinanceModel.objects.bulk_create(finances)
        make_case('Malla sin bloque', None)
        make_case('Malla sin bloque inactivo', None, active=False)

        missing = CaseModel.objects.exclude(pk__in=self.covered())
        self.assertEqual(missing.count(), 0, list(
            missing.values_list('client__full_name', flat=True)[:5]
        ))

    def test_las_categorias_de_dinero_no_se_pisan_sin_motivo(self):
        """
        Deudores y expectativas se excluyen entre si y de pagados/sin cifras:
        el solapamiento permitido es solo cuota litis fija cubierta, que sale
        en «Pagados» y en su cuadro.
        """
        call_command('seed_gestor_demo', stdout=StringIO())
        debtors = set(CaseFinanceModel.objects.debtors()
                      .values_list('case_id', flat=True))
        expectations = set(CaseFinanceModel.objects.expectations()
                           .values_list('case_id', flat=True))
        by_key = boxes()
        paid = by_key['paid_in_full'].case_ids
        unclassified = by_key['unclassified'].case_ids
        fixed = by_key['fixed_contingency'].case_ids

        self.assertEqual(debtors & expectations, set())
        self.assertEqual(debtors & paid, set())
        self.assertEqual(debtors & fixed, set())
        self.assertEqual(unclassified & (debtors | expectations | paid | fixed), set())
        overlap = paid & fixed
        for case_id in overlap:
            finance = CaseFinanceModel.objects.get(case_id=case_id)
            self.assertEqual(finance.mandate, Mandate.CONTINGENCY)
            self.assertEqual(finance.contingency_percentage, 0)


class DashboardBoxPageTests(TestCase):
    """La pantalla: el mismo patron de tabla que los cuadros de siempre."""

    @classmethod
    def setUpTestData(cls):
        make_user('abogada', gestor=True)

    def setUp(self):
        login_as(self.client, 'abogada')
        self.url = reverse('case_manager:gestor_dashboard')

    def test_vacio_cada_cuadro_lleva_aviso_y_ninguna_fila_colspan(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn('colspan', html)
        for box in build_boxes():
            self.assertContains(response, f'id="{box.table_id}"')
            self.assertContains(response, f'data-dashboard-box="{box.key}"')
        self.assertEqual(html.count('data-dashboard-box='), len(build_boxes()))
        # Un aviso `data-dt-fallback` por tabla vacia (mas los de siempre).
        self.assertGreaterEqual(
            html.count('data-dt-fallback'), len(build_boxes())
        )
        self.assertContains(response, 'data-dt-empty=', count=None)

    def test_con_datos_pinta_el_asunto_con_su_enlace(self):
        case = make_case('Cliente Pagado', Mandate.PAYMENT,
                         agreed_fee=4_000_000, paid_amount=4_000_000,
                         authorized=True)

        response = self.client.get(self.url)

        self.assertContains(
            response,
            reverse('case_manager:gestor_case_update', args=[case.pk]),
        )
        self.assertContains(response, 'Cliente Pagado')
        self.assertRegex(response.content.decode(), r'\$4[.,]000[.,]000')
        self.assertContains(response, 'Authorized')

    def test_las_consultas_no_crecen_con_las_filas(self):
        def galeria(n):
            for i in range(n):
                make_case(f'P{n}-{i}', Mandate.PAYMENT, agreed_fee=1_000_000,
                          paid_amount=1_000_000, authorized=bool(i % 2))
                make_case(f'G{n}-{i}', Mandate.PRO_BONO)
                make_case(f'I{n}-{i}', Mandate.PAYMENT, active=False,
                          agreed_fee=1_000_000)
                make_case(f'H{n}-{i}', Mandate.PAYMENT, show=False,
                          agreed_fee=1_000_000)
                make_case(f'N{n}-{i}', None)

        galeria(1)
        with CaptureQueriesContext(connection) as few:
            build_boxes()
        galeria(6)
        with CaptureQueriesContext(connection) as many:
            build_boxes()

        self.assertEqual(len(few), len(many))
        self.assertLessEqual(len(many), 8)

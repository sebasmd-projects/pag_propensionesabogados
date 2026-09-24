"""
Los calculos financieros del gestor.

Son la actividad que la cotizacion llama «procesos criticos»: cada cifra de
estas es plata que alguien cobra o deja de cobrar. Hasta ahora vivian en
`actualizarPanelGerencial()`, en JavaScript, sin una sola prueba.

Las dos reglas que estas pruebas existen para sostener:

1. `Cuota litis` al 0 % **no es una expectativa**: es un valor fijo cerrado,
   y cuenta como deuda.
2. El saldo nunca es negativo.
"""

from django.test import TestCase
from django.template.loader import render_to_string

from ..choices import Mandate, Service, Stage
from ..models import CaseFinanceModel, CaseModel, ClientModel
from ..forms import CaseFinanceForm, CaseForm, CaseFinanceFormSet


class FreeModalityFormTests(TestCase):
    def test_initial_fields_follow_modality_before_javascript(self):
        for mandate in (Mandate.PRO_BONO, Mandate.GUARDIANSHIP,
                        Mandate.PAYMENT, Mandate.CONTINGENCY):
            with self.subTest(mandate=mandate):
                form = CaseFinanceForm(initial={
                    'mandate': mandate, 'contingency_percentage': 20,
                })
                for name in ('agreed_fee', 'paid_amount', 'contingency_value'):
                    visible = (mandate == Mandate.PAYMENT and name != 'contingency_value') or (
                        mandate == Mandate.CONTINGENCY and name == 'contingency_value'
                    )
                    html = render_to_string('case_manager/gestor/partials/field.html', {'field': form[name]})
                    self.assertEqual(' hidden' in html, not visible)

    def test_form_delivers_payment_logic_without_external_static_file(self):
        html = render_to_string('case_manager/gestor/case_form.html', {
            'form': CaseForm(), 'finance_formset': CaseFinanceFormSet(),
        })
        self.assertNotIn('/static/assets/custom/js/payment_form.js', html)
        self.assertNotIn('/static/assets/custom/js/case_form.js', html)
        self.assertIn("mandate.addEventListener('change'", html)
        self.assertIn('servicio gratuito', html)

    def test_free_modalities_save_without_amounts(self):
        for mandate in (Mandate.PRO_BONO, Mandate.GUARDIANSHIP):
            with self.subTest(mandate=mandate):
                form = CaseFinanceForm(data={'mandate': mandate})
                self.assertTrue(form.is_valid(), form.errors)
                finance = form.save(commit=False)
                self.assertEqual(finance.agreed, 0)
                self.assertEqual(finance.paid, 0)
                self.assertEqual(finance.balance, 0)
                self.assertEqual(finance.expectation, 0)

    def test_switching_to_free_clears_previous_amounts_on_server(self):
        for index, mandate in enumerate((Mandate.PRO_BONO, Mandate.GUARDIANSHIP)):
            with self.subTest(mandate=mandate):
                finance = make_case(identification=str(90000 + index),
                                    agreed_fee=5000000, paid_amount=1000000)
                form = CaseFinanceForm(instance=finance, data={
                    'mandate': mandate, 'agreed_fee': '5000000',
                    'paid_amount': '1000000', 'contingency_value': 'invalid',
                    'contingency_percentage': '30',
                })
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                finance.refresh_from_db()
                for name in ('agreed_fee', 'paid_amount', 'contingency_value',
                             'contingency_percentage'):
                    self.assertEqual(getattr(finance, name), 0)


def make_case(identification='1000000001', name='Ana Perez', **finance):
    client = ClientModel.objects.create(
        identification=identification, full_name=name,
        email='cliente@example.test'
        )
    case = CaseModel.objects.create(
        client=client,
        service=Service.JUDICIAL,
        stage=Stage.IN_PROGRESS,
    )
    finance.setdefault('mandate', Mandate.PAYMENT)
    return CaseFinanceModel.objects.create(case=case, **finance)


class BalanceTests(TestCase):
    """`CaseFinanceModel.balance`: lo que falta por cobrar."""

    def test_modalidad_de_pago_debe_la_resta(self):
        finance = make_case(agreed_fee=3_000_000, paid_amount=1_000_000)

        self.assertEqual(finance.agreed, 3_000_000)
        self.assertEqual(finance.paid, 1_000_000)
        self.assertEqual(finance.balance, 2_000_000)

    def test_el_saldo_nunca_es_negativo(self):
        """
        Un abono mayor que lo pactado es un error de captura o un anticipo.
        En ninguno de los dos casos el panel ensena saldo a favor.
        """
        finance = make_case(agreed_fee=1_000_000, paid_amount=1_500_000)

        self.assertEqual(finance.balance, 0)

    def test_cuota_litis_al_cero_por_ciento_se_debe_entera(self):
        """Valor fijo cerrado: esta pactado y no se ha cobrado nada."""
        finance = make_case(
            mandate=Mandate.CONTINGENCY,
            contingency_percentage=0,
            contingency_value=5_000_000,
        )

        self.assertFalse(finance.is_contingency_expectation)
        self.assertEqual(finance.agreed, 5_000_000)
        self.assertEqual(finance.balance, 5_000_000)
        self.assertEqual(finance.expectation, 0)

    def test_cuota_litis_sobre_cero_es_expectativa_y_no_deuda(self):
        finance = make_case(
            mandate=Mandate.CONTINGENCY,
            contingency_percentage=30,
            contingency_value=8_000_000,
        )

        self.assertTrue(finance.is_contingency_expectation)
        self.assertEqual(finance.agreed, 0)
        self.assertEqual(finance.balance, 0)
        self.assertEqual(finance.expectation, 8_000_000)

    def test_ad_honorem_y_curaduria_no_mueven_dinero(self):
        casos = ((Mandate.PRO_BONO, '3001'), (Mandate.GUARDIANSHIP, '3002'))
        for mandate, identification in casos:
            with self.subTest(mandate=mandate):
                finance = make_case(
                    identification=identification,
                    mandate=mandate,
                )
                self.assertEqual(finance.agreed, 0)
                self.assertEqual(finance.balance, 0)
                self.assertEqual(finance.expectation, 0)


class DashboardTotalsTests(TestCase):
    """
    `CaseFinanceQuerySet.totals()`: las cifras de cabecera.

    El escenario es el mismo en todas: cuatro casos, uno de cada forma de
    cobrar, para que cada total tenga que distinguirlos.
    """

    def setUp(self):
        make_case('1001', 'Uno', agreed_fee=3_000_000, paid_amount=1_000_000)
        make_case('1002', 'Dos', agreed_fee=1_000_000, paid_amount=1_000_000)
        make_case(
            '1003', 'Tres',
            mandate=Mandate.CONTINGENCY,
            contingency_percentage=0,
            contingency_value=2_000_000,
        )
        make_case(
            '1004', 'Cuatro',
            mandate=Mandate.CONTINGENCY,
            contingency_percentage=20,
            contingency_value=10_000_000,
        )

    def test_los_totales(self):
        totals = CaseFinanceModel.objects.totals()

        # Pactado: 3.000.000 + 1.000.000 de las modalidades de pago, mas los
        # 2.000.000 de la cuota litis fija. La expectativa no esta pactada.
        self.assertEqual(totals['agreed'], 6_000_000)
        self.assertEqual(totals['paid'], 2_000_000)
        # Saldo: 2.000.000 del primero, 0 del segundo, 2.000.000 del fijo.
        self.assertEqual(totals['balance'], 4_000_000)
        self.assertEqual(totals['expectation'], 10_000_000)
        self.assertEqual(totals['potential_pending'], 14_000_000)
        self.assertEqual(totals['projected_total'], 16_000_000)

    def test_lo_excluido_del_panel_no_suma(self):
        """`show_in_dashboard` es del despacho, y se respeta en los totales."""
        CaseFinanceModel.objects.filter(
            case__client__identification='1004'
        ).update(show_in_dashboard=False)

        totals = CaseFinanceModel.objects.totals()

        self.assertEqual(totals['expectation'], 0)
        self.assertEqual(totals['potential_pending'], 4_000_000)

    def test_un_caso_sin_vigencia_no_suma(self):
        """Los totales miran casos vivos, igual que el portal."""
        CaseModel.objects.filter(
            client__identification='1001'
        ).update(is_active=False)

        totals = CaseFinanceModel.objects.totals()

        self.assertEqual(totals['agreed'], 3_000_000)
        self.assertEqual(totals['paid'], 1_000_000)
        self.assertEqual(totals['balance'], 2_000_000)

    def test_los_totales_se_piden_en_una_sola_consulta(self):
        """
        Seis cifras, una consulta.

        No es microoptimizacion: el panel las pinta juntas y calcularlas en
        Python obligaria a traerse todas las filas del despacho.
        """
        with self.assertNumQueries(1):
            CaseFinanceModel.objects.totals()


class DebtorsAndExpectationsTests(TestCase):
    """
    Las dos listas del panel gerencial.

    Que sean dos consultas y no dos tablas es la decision de modelo que estas
    pruebas fijan: si alguna vez se materializan, tienen que seguir dando
    esto.
    """

    def setUp(self):
        make_case('2001', 'Debe', agreed_fee=5_000_000, paid_amount=1_000_000)
        make_case('2002', 'Al dia', agreed_fee=5_000_000, paid_amount=5_000_000)
        make_case(
            '2003', 'Fijo',
            mandate=Mandate.CONTINGENCY,
            contingency_percentage=0,
            contingency_value=3_000_000,
        )
        make_case(
            '2004', 'Expectativa',
            mandate=Mandate.CONTINGENCY,
            contingency_percentage=40,
            contingency_value=9_000_000,
        )
        make_case('2005', 'Gratis', mandate=Mandate.PRO_BONO)

    def test_deudores_son_los_que_deben_hoy(self):
        identifications = set(
            CaseFinanceModel.objects.debtors().values_list(
                'case__client__identification', flat=True
            )
        )

        # El que debe, y el de cuota litis fija que aun no ha pagado nada.
        self.assertEqual(identifications, {'2001', '2003'})

    def test_quien_esta_al_dia_no_es_deudor(self):
        self.assertNotIn(
            '2002',
            CaseFinanceModel.objects.debtors().values_list(
                'case__client__identification', flat=True
            ),
        )

    def test_una_expectativa_no_es_una_deuda(self):
        """La confusion que mas caro sale: no se le puede cobrar."""
        self.assertNotIn(
            '2004',
            CaseFinanceModel.objects.debtors().values_list(
                'case__client__identification', flat=True
            ),
        )

    def test_expectativas_son_solo_la_cuota_litis_sobre_cero(self):
        identifications = set(
            CaseFinanceModel.objects.expectations().values_list(
                'case__client__identification', flat=True
            )
        )

        self.assertEqual(identifications, {'2004'})

    def test_las_dos_listas_no_se_solapan(self):
        """
        Ninguna fila puede estar en las dos.

        Si se solaparan, el pendiente potencial contaria dos veces el mismo
        dinero, que es exactamente el error que la pantalla advierte al
        separarlas.
        """
        debtors = set(
            CaseFinanceModel.objects.debtors().values_list('pk', flat=True)
        )
        expectations = set(
            CaseFinanceModel.objects.expectations().values_list('pk', flat=True)
        )

        self.assertEqual(debtors & expectations, set())


class PortfolioChartTests(TestCase):
    """
    Las dos cifras que solo existen para que se dibuje el panel.

    Se prueban porque un porcentaje mal calculado no da error: pinta un aro
    con los tramos cambiados, y quien lo mira se cree lo que ve.
    """

    def caso(self, **finanzas):
        cliente = ClientModel.objects.create(
            identification=f'{CaseFinanceModel.objects.count() + 1:08d}',
            full_name='Cliente de prueba',
            email='cliente{CaseFinanceModel.objects.count() + 1:08d}@example.test'
        )
        caso = CaseModel.objects.create(
            client=cliente, service=Service.JUDICIAL, stage=Stage.IN_PROGRESS,
            area=finanzas.pop('area', 'Civil'),
        )
        return CaseFinanceModel.objects.create(case=caso, **finanzas)

    def test_los_tres_tramos_del_anillo_cierran_el_circulo(self):
        """
        El segundo corte es **acumulado**: un `conic-gradient` dibuja donde
        termina cada tramo, no su ancho. Si se le pasara el ancho, el tramo
        de «por cobrar» empezaria donde tiene que acabar y el aro saldria con
        los colores corridos.
        """
        self.caso(mandate=Mandate.PAYMENT, agreed_fee=1_000_000,
                  paid_amount=250_000)
        self.caso(mandate=Mandate.CONTINGENCY, contingency_percentage=30,
                  contingency_value=1_000_000)

        totals = CaseFinanceModel.objects.totals()

        # pagado 250 000, por cobrar 750 000, expectativa 1 000 000
        self.assertEqual(totals['projected_total'], 2_000_000)
        self.assertEqual(totals['share_paid'], 12.5)
        self.assertEqual(totals['share_balance'], 50.0)
        self.assertGreaterEqual(totals['share_balance'], totals['share_paid'])

    def test_la_tasa_de_recaudo_se_mide_sobre_el_total_proyectado(self):
        """
        No sobre lo pactado, que es la otra lectura posible y da otro numero.
        Un despacho con mucha cuota litis sin resolver tiene la tasa baja
        aunque haya cobrado todo lo cierto, y eso es lo que el anillo dice.
        """
        self.caso(mandate=Mandate.PAYMENT, agreed_fee=1_000_000,
                  paid_amount=1_000_000)
        self.caso(mandate=Mandate.CONTINGENCY, contingency_percentage=30,
                  contingency_value=3_000_000)

        self.assertEqual(
            CaseFinanceModel.objects.totals()['collection_rate'], 25
        )

    def test_una_cartera_vacia_no_divide_por_cero(self):
        totals = CaseFinanceModel.objects.totals()

        self.assertEqual(totals['collection_rate'], 0)
        self.assertEqual(totals['share_paid'], 0)
        self.assertEqual(totals['share_balance'], 0)

    def test_el_reparto_por_area_va_de_mas_a_menos(self):
        self.caso(area='Civil', mandate=Mandate.PAYMENT, agreed_fee=1_000_000)
        self.caso(area='Familia', mandate=Mandate.PAYMENT,
                  agreed_fee=3_000_000)

        areas = CaseFinanceModel.objects.by_area()

        self.assertEqual([row['area'] for row in areas], ['Familia', 'Civil'])
        self.assertEqual([row['share'] for row in areas], [75, 25])

    def test_un_asunto_sin_area_no_se_queda_sin_nombre(self):
        """
        `area` puede estar vacio, y una barra con la etiqueta en blanco es una
        barra que nadie sabe de que es.
        """
        self.caso(area='', mandate=Mandate.PAYMENT, agreed_fee=1_000_000)

        self.assertEqual(
            CaseFinanceModel.objects.by_area()[0]['area'], 'No area recorded'
        )

    def test_lo_excluido_del_panel_no_entra_en_el_reparto(self):
        """
        La casilla «no incluir en panel economico» tiene que valer tambien
        aqui; si no, una cifra saldria en el aro y no en las tarjetas.
        """
        self.caso(area='Civil', mandate=Mandate.PAYMENT,
                  agreed_fee=1_000_000, show_in_dashboard=False)

        self.assertEqual(CaseFinanceModel.objects.by_area(), [])


class ManagerExposeLasPreguntasTests(TestCase):
    """
    Que el gestor del modelo expone lo que el panel le pide.

    `CaseFinanceQuerySet` se instala con `as_manager()`, que copia sus metodos
    publicos al gestor. Es automatico, asi que parece que no hay nada que
    probar; lo que se rompe en silencio es lo otro: mover un metodo fuera de
    la clase --o sangrarlo mal-- lo deja como funcion suelta, el modulo sigue
    importando, las pruebas que lo llaman directamente siguen pasando, y lo
    unico que falla es la pantalla, con un `AttributeError` en produccion.
    """

    def test_el_gestor_tiene_las_preguntas_del_panel(self):
        for nombre in ('in_dashboard', 'debtors', 'expectations',
                       'totals', 'by_area'):
            with self.subTest(pregunta=nombre):
                self.assertTrue(
                    hasattr(CaseFinanceModel.objects, nombre),
                    f'`CaseFinanceModel.objects.{nombre}` no existe: '
                    f'seguramente se salio de `CaseFinanceQuerySet`.',
                )

    def test_y_se_pueden_llamar_sobre_una_base_vacia(self):
        """
        Tenerlo no basta: `totals()` y `by_area()` devuelven estructuras, no
        querysets, y un despacho recien instalado no tiene ni una fila.
        """
        self.assertEqual(CaseFinanceModel.objects.totals()['agreed'], 0)
        self.assertEqual(CaseFinanceModel.objects.by_area(), [])

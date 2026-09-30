"""
El gestor interno como pantallas del sitio.

Se prueban **pidiendo las paginas y enviando los formularios**, no llamando a
los metodos por dentro. Es la leccion del `TypeError` del inline del admin:
comprobar las piezas sueltas dejaba pasar un fallo que reventaba en cuanto
alguien abria la pagina.

Lo que mas se cuida aqui son dos cosas:

1. **La puerta.** Cada pantalla ensena el dinero del despacho, asi que el que
   entra sin grupo tiene que rebotar en todas, no en la primera.
2. **Que el asunto y su dinero se guarden juntos.** Son dos formularios y un
   boton; si uno pasara sin el otro quedaria un expediente a medias que no
   suma en ningun panel y que nadie sabria que esta roto.
"""

from io import StringIO
from pathlib import Path
import json
from datetime import date, timedelta

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..choices import Court, Mandate, Procedure, Service, Stage
from ..models import CaseFinanceModel, CaseModel, ClientModel
from .test_access import login_as, make_user
from .test_public_access import identificarse

CLAVE = 'una-contrasena-larga-de-verdad'


class GestorAccessTests(TestCase):
    """
    Quien puede abrir cada pantalla.

    Se recorren **todas** las rutas del gestor en cada caso. Proteger la
    primera y olvidarse de la cuarta es como se filtra el panel economico.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())

        cls.client_record = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test'
        )
        cls.case = CaseModel.objects.create(
            client=cls.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )

        cls.rutas = [
            reverse('case_manager:gestor_dashboard'),
            reverse('case_manager:gestor_client_list'),
            reverse('case_manager:gestor_client_create'),
            reverse('case_manager:gestor_client_update',
                    args=[cls.client_record.pk]),
            reverse('case_manager:gestor_case_list'),
            reverse('case_manager:gestor_case_create'),
            reverse('case_manager:gestor_case_update', args=[cls.case.pk]),
        ]

    def test_un_visitante_va_al_acceso(self):
        """Sin sesion, al formulario de entrada: ahi se arregla entrando."""
        for ruta in self.rutas:
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)

                self.assertEqual(respuesta.status_code, 302)
                self.assertIn('login', respuesta['Location'])

    def test_una_cuenta_sin_el_grupo_recibe_404(self):
        """
        404 y no 403.

        Un 403 confirma que en esa direccion hay algo; un 404 no dice nada.
        Registrarse en el sitio es publico, asi que cualquiera puede llegar
        aqui con una sesion valida.
        """
        make_user('cliente')
        login_as(self.client, 'cliente')

        for ruta in self.rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_el_grupo_del_gestor_entra_en_todas(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

        for ruta in self.rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_un_superusuario_entra_en_todas(self):
        make_user('jefe', superuser=True)
        login_as(self.client, 'jefe')

        for ruta in self.rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_una_cuenta_desactivada_no_entra(self):
        make_user('exempleado', gestor=True, active=False)
        login_as(self.client, 'exempleado')

        respuesta = self.client.get(self.rutas[0])

        self.assertIn(respuesta.status_code, (302, 404))

    def test_el_gestor_no_se_abre_sin_sesion_ni_para_el_dinero(self):
        """Lo que sostiene todo lo demas: el panel no se sirve a nadie mas."""
        respuesta = self.client.get(reverse('case_manager:gestor_dashboard'))

        self.assertNotEqual(respuesta.status_code, 200)


class GestorDashboardTests(TestCase):
    """El panel economico, con las cifras que ya prueba `test_finance`."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cls.url = reverse('case_manager:gestor_dashboard')

        deudor = ClientModel.objects.create(
            identification='1001', full_name='Deudor Uno',
            email='cliente1001@example.test'
        )
        caso = CaseModel.objects.create(
            client=deudor, service=Service.JUDICIAL, stage=Stage.IN_PROGRESS
        )
        CaseFinanceModel.objects.create(
            case=caso, mandate=Mandate.PAYMENT,
            agreed_fee=5_000_000, paid_amount=1_000_000,
        )

        expectante = ClientModel.objects.create(
            identification='1002', full_name='Expectativa Dos',
            email='cliente1002@example.test'
        )
        caso2 = CaseModel.objects.create(
            client=expectante, service=Service.JUDICIAL, stage=Stage.FINAL_STAGE
        )
        CaseFinanceModel.objects.create(
            case=caso2, mandate=Mandate.CONTINGENCY,
            contingency_percentage=30, contingency_value=9_000_000,
        )

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

    def test_las_cifras_son_las_del_modelo(self):
        respuesta = self.client.get(self.url)

        totals = respuesta.context['totals']
        self.assertEqual(totals['agreed'], 5_000_000)
        self.assertEqual(totals['paid'], 1_000_000)
        self.assertEqual(totals['balance'], 4_000_000)
        self.assertEqual(totals['expectation'], 9_000_000)
        self.assertEqual(totals['potential_pending'], 13_000_000)

    def test_el_comparativo_se_renderiza_como_grafica_de_columnas(self):
        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, 'gestor-time-chart')
        self.assertContains(respuesta, 'bi-graph-up-arrow')
        self.assertNotContains(respuesta, 'Portfolio financial status')
        self.assertNotContains(respuesta, 'bi-pie-chart')

    def test_las_cinco_series_son_filtros_y_hay_torta_con_los_mismos_datos(self):
        respuesta = self.client.get(self.url)

        for key in ('agreed', 'paid', 'balance', 'expectation', 'upcoming'):
            self.assertContains(respuesta, f'data-series-toggle="{key}"')
            self.assertContains(respuesta, f'data-pie-item="{key}"')
        self.assertContains(respuesta, 'type="checkbox" checked data-series-toggle')
        self.assertContains(respuesta, 'data-financial-pie')
        totals = {row['key']: row['value'] for row in respuesta.context['financial_chart']['totals']}
        self.assertEqual(totals['agreed'], 5_000_000)
        self.assertEqual(totals['expectation'], 9_000_000)
        css = (Path(settings.BASE_DIR) / 'public/staticfiles/assets/custom/css/gestor.css').read_text(encoding='utf-8')
        self.assertIn('overflow-x: hidden', css)

    def test_el_comparativo_abre_en_el_mes_actual_agrupado_por_semanas(self):
        respuesta = self.client.get(self.url)
        chart = respuesta.context['financial_chart']
        today = timezone.localdate()

        self.assertEqual(chart['start'], today.replace(day=1).isoformat())
        self.assertEqual(chart['granularity'], 'week')
        self.assertFalse(chart['is_all'])
        totals = {
            item['key']: sum(
                value['value'] for bucket in chart['buckets']
                for value in bucket['values'] if value['key'] == item['key']
            )
            for item in chart['legend']
        }
        self.assertEqual(totals['agreed'], 5_000_000)
        self.assertEqual(totals['paid'], 1_000_000)
        self.assertEqual(totals['balance'], 4_000_000)
        self.assertEqual(totals['expectation'], 9_000_000)

    def test_el_rango_cambia_automaticamente_la_agrupacion(self):
        today = timezone.localdate()
        for days, expected in (
            (0, 'day'), (6, 'day'), (7, 'week'), (30, 'week'), (31, 'month'),
            (60, 'month'), (365, 'month'), (366, 'year'), (1000, 'year'),
        ):
            with self.subTest(days=days):
                response = self.client.get(self.url, {
                    'start': (today - timedelta(days=days)).isoformat(),
                    'end': today.isoformat(),
                })
                self.assertEqual(
                    response.context['financial_chart']['granularity'], expected
                )

    def test_pagos_y_proximos_pagos_usan_sus_fechas(self):
        today = timezone.localdate()
        finance = CaseFinanceModel.objects.get(mandate=Mandate.PAYMENT)
        finance.payment_history = [
            {'kind': 'payment', 'amount': 1_000_000,
             'date': today.isoformat(), 'next_date': ''},
            {'kind': 'expected', 'amount': 2_000_000,
             'date': today.isoformat(), 'next_date': ''},
        ]
        finance.save(update_fields=['payment_history'])

        response = self.client.get(self.url)
        chart = response.context['financial_chart']
        bucket = next(row for row in chart['buckets']
                      if row['start'] <= today.isoformat() <= row['end'])
        values = {row['key']: row['value'] for row in bucket['values']}

        self.assertEqual(values['paid'], 1_000_000)
        self.assertEqual(values['upcoming'], 2_000_000)

    def test_un_rango_invertido_regresa_al_mes_actual(self):
        today = timezone.localdate()
        response = self.client.get(self.url, {
            'start': today.isoformat(),
            'end': (today - timedelta(days=1)).isoformat(),
        })

        chart = response.context['financial_chart']
        self.assertEqual(chart['start'], today.replace(day=1).isoformat())
        self.assertEqual(chart['granularity'], 'week')

    def test_desde_el_inicio_toma_el_primer_registro(self):
        old_client = ClientModel.objects.create(
            identification='1003', full_name='Histórico Tres'
        )
        old_case = CaseModel.objects.create(
            client=old_client, service=Service.JUDICIAL, stage=Stage.IN_PROGRESS
        )
        CaseFinanceModel.objects.create(
            case=old_case, start_date=date(2018, 2, 1),
            mandate=Mandate.PAYMENT, agreed_fee=500_000,
        )

        respuesta = self.client.get(self.url, {'range': 'all'})
        chart = respuesta.context['financial_chart']

        self.assertTrue(chart['is_all'])
        self.assertEqual(chart['start'], '2018-02-01')
        self.assertEqual(chart['granularity'], 'year')

    # ---- Agrupación según la duración del rango ----

    def _chart(self, start, end):
        response = self.client.get(self.url, {'start': start, 'end': end})
        return response.context['financial_chart']

    def test_un_dia_es_un_solo_grupo_diario(self):
        chart = self._chart('2026-09-15', '2026-09-15')

        self.assertEqual(chart['granularity'], 'day')
        self.assertEqual([b['label'] for b in chart['buckets']], ['15/09'])

    def test_una_semana_se_separa_en_siete_dias(self):
        chart = self._chart('2026-09-01', '2026-09-07')

        self.assertEqual(chart['granularity'], 'day')
        self.assertEqual(len(chart['buckets']), 7)
        self.assertEqual(chart['buckets'][0]['label'], '01/09')
        self.assertEqual(chart['buckets'][-1]['label'], '07/09')

    def test_septiembre_se_separa_en_cinco_semanas_de_lunes_a_domingo(self):
        chart = self._chart('2026-09-01', '2026-09-30')

        self.assertEqual(chart['granularity'], 'week')
        self.assertEqual(
            [(b['start'], b['end']) for b in chart['buckets']],
            [('2026-09-01', '2026-09-06'), ('2026-09-07', '2026-09-13'),
             ('2026-09-14', '2026-09-20'), ('2026-09-21', '2026-09-27'),
             ('2026-09-28', '2026-09-30')],
        )
        # Las semanas completas empiezan en lunes y terminan en domingo.
        for bucket in chart['buckets'][1:4]:
            self.assertEqual(date.fromisoformat(bucket['start']).weekday(), 0)
            self.assertEqual(date.fromisoformat(bucket['end']).weekday(), 6)
        self.assertEqual(
            [b['label'] for b in chart['buckets']],
            ['01–06 sep', '07–13 sep', '14–20 sep', '21–27 sep', '28–30 sep'],
        )
        self.assertEqual(chart['buckets'][0]['title'], '01–06 sep 2026')

    def test_una_semana_que_cruza_de_mes_lo_dice_en_su_etiqueta(self):
        chart = self._chart('2026-09-21', '2026-10-05')

        self.assertEqual(chart['buckets'][1]['label'], '28 sep–04 oct')

    def test_un_anio_se_separa_en_doce_meses(self):
        chart = self._chart('2026-01-01', '2026-12-31')

        self.assertEqual(chart['granularity'], 'month')
        self.assertEqual(len(chart['buckets']), 12)
        self.assertEqual(chart['buckets'][0]['label'], 'ene 2026')
        self.assertEqual(chart['buckets'][-1]['label'], 'dic 2026')

    def test_mas_de_un_anio_se_separa_en_anios(self):
        chart = self._chart('2024-06-01', '2026-03-01')

        self.assertEqual(chart['granularity'], 'year')
        self.assertEqual([b['label'] for b in chart['buckets']],
                         ['2024', '2025', '2026'])

    def test_completo_se_separa_en_anios(self):
        old_client = ClientModel.objects.create(
            identification='1004', full_name='Histórico Cuatro'
        )
        old_case = CaseModel.objects.create(
            client=old_client, service=Service.JUDICIAL, stage=Stage.IN_PROGRESS
        )
        CaseFinanceModel.objects.create(
            case=old_case, start_date=date(2023, 5, 1),
            mandate=Mandate.PAYMENT, agreed_fee=500_000,
        )

        chart = self.client.get(self.url, {'range': 'all'}).context['financial_chart']

        self.assertEqual(chart['granularity'], 'year')
        labels = [b['label'] for b in chart['buckets']]
        self.assertEqual(labels[0], '2023')
        self.assertEqual(labels[-1], str(timezone.localdate().year))
        self.assertEqual(len(labels), timezone.localdate().year - 2023 + 1)

    def test_el_eje_y_se_abrevia_segun_la_escala(self):
        from ..financial_chart import axis_ticks

        top, ticks = axis_ticks(194_686_043)
        self.assertEqual(top, 200_000_000)
        self.assertEqual([t['label'] for t in ticks],
                         ['$0 M', '$50 M', '$100 M', '$150 M', '$200 M'])
        top, ticks = axis_ticks(42_000)
        self.assertEqual([t['label'] for t in ticks][-1], '$60 K')
        self.assertEqual(axis_ticks(0)[1][0]['label'], '$0 M')

    # ---- Botones de periodo, tooltip y filtros independientes ----

    def test_los_botones_de_periodo_rapido_estan_junto_a_las_fechas(self):
        today = timezone.localdate()
        html = self.client.get(self.url).content.decode()

        for key, label in (('day', 'Día'), ('week', 'Semana'), ('month', 'Mes'),
                           ('year', 'Año'), ('all', 'Completo')):
            self.assertIn(f'data-period="{key}"', html)
            self.assertIn(f'>{label}</a>', html)
        self.assertIn('href="?range=all"', html)
        self.assertIn(
            f'href="?start={today.isoformat()}&amp;end={today.isoformat()}"', html
        )
        self.assertLess(html.index('data-financial-periods'),
                        html.index('data-financial-range'))

    def test_solo_el_periodo_vigente_esta_marcado(self):
        today = timezone.localdate()
        cases = (
            ({}, 'month'),
            ({'start': today.isoformat(), 'end': today.isoformat()}, 'day'),
            ({'start': today.replace(month=1, day=1).isoformat(),
              'end': today.replace(month=12, day=31).isoformat()}, 'year'),
            ({'range': 'all'}, 'all'),
        )
        for params, expected in cases:
            with self.subTest(expected=expected):
                response = self.client.get(self.url, params)
                active = [p['key'] for p in response.context['financial_chart']['periods']
                          if p['active']]
                self.assertEqual(active, [expected])
                self.assertContains(response, 'aria-current="true"', count=1)

    def test_semana_actual_va_de_lunes_a_domingo(self):
        today = timezone.localdate()
        response = self.client.get(self.url)
        week = next(p for p in response.context['financial_chart']['periods']
                    if p['key'] == 'week')
        monday = today - timedelta(days=today.weekday())

        self.assertEqual(
            week['url'],
            f'?start={monday.isoformat()}&end={(monday + timedelta(days=6)).isoformat()}',
        )

    def test_la_grafica_expone_el_tooltip_y_el_eje(self):
        response = self.client.get(self.url, {'start': '2026-09-01', 'end': '2026-09-30'})

        self.assertContains(response, 'data-chart-tooltip role="tooltip"')
        self.assertContains(response, 'data-chart-axis')
        self.assertContains(response, '$0 M')
        self.assertContains(response, 'data-title="07–13 sep 2026"')
        self.assertContains(response, 'data-name="Pagado"')
        self.assertContains(response, 'data-value=')
        self.assertContains(response, 'gestor-time-labels')
        html = response.content.decode()
        self.assertEqual(html.count('<div class="gestor-time-bucket"'), 5)

    def test_barras_y_torta_tienen_filtros_independientes(self):
        html = self.client.get(self.url).content.decode()

        bars_block = html[html.index('aria-label="Filtro de series de las barras"'):html.index('data-time-chart')]
        pie_block = html[html.index('aria-label="Filtro de series de la torta"'):html.index('data-pie-empty')]
        for key in ('agreed', 'paid', 'balance', 'expectation', 'upcoming'):
            self.assertIn(f'data-series-toggle="{key}"', bars_block)
            self.assertNotIn('data-pie-toggle', bars_block)
            self.assertIn(f'data-pie-toggle="{key}"', pie_block)
            self.assertNotIn('data-series-toggle', pie_block)
        self.assertEqual(pie_block.count('aria-pressed="true"'), 5)
        self.assertEqual(pie_block.count('<button type="button"'), 5)
        self.assertIn('aria-label="Filtro de series de las barras"', bars_block)
        self.assertIn('aria-label="Filtro de series de la torta"', pie_block)

    def test_exporta_el_panel_para_la_prueba_dom(self):
        import os
        directory = os.environ.get('CASE_FLOW_HTML_DIR')
        if not directory:
            self.skipTest('CASE_FLOW_HTML_DIR no definido')
        response = self.client.get(self.url, {'start': '2026-09-01', 'end': '2026-09-30'})
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        (target / 'dashboard.html').write_bytes(response.content)
        partial = self.client.get(
            self.url, {'range': 'all'}, HTTP_X_REQUESTED_WITH='fetch'
        )
        (target / 'chart_partial.html').write_bytes(partial.content)

    def test_marca_de_parcial_devuelve_solo_el_bloque_del_grafico(self):
        response = self.client.get(
            self.url, {'start': '2026-09-01', 'end': '2026-09-30'},
            HTTP_X_REQUESTED_WITH='fetch',
        )
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('X-Requested-With', response.headers['Vary'])
        self.assertNotIn('<html', html)
        self.assertNotIn('Próximos pagos', html)
        self.assertTemplateNotUsed(response, 'case_manager/gestor/dashboard.html')
        self.assertTemplateUsed(response, 'case_manager/gestor/partials/financial_chart_block.html')
        for marker in ('data-financial-chart', 'data-time-chart', 'data-financial-pie',
                       'data-financial-periods', 'data-financial-range'):
            self.assertIn(marker, html)
        self.assertNotIn('<script', html)
        self.assertIn('value="2026-09-01"', html)
        self.assertIn('value="2026-09-30"', html)
        self.assertIn('Agrupado por semanas', html)

    def test_parcial_marca_el_periodo_activo_del_rango_pedido(self):
        hoy = timezone.localdate()
        response = self.client.get(self.url, {'range': 'all'}, HTTP_X_REQUESTED_WITH='fetch')
        html = response.content.decode()
        self.assertIn('Agrupado por años', html)
        marca = html.index('data-period="all"')
        completo = html[html.rindex('<a', 0, marca):html.index('>', marca)]
        self.assertIn('active', completo)
        self.assertEqual(html.count('aria-current="true"'), 1)

        fin_de_mes = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        response = self.client.get(
            self.url, {'start': hoy.replace(day=1).isoformat(), 'end': fin_de_mes.isoformat()},
            HTTP_X_REQUESTED_WITH='fetch',
        )
        activos = [p['key'] for p in response.context['financial_chart']['periods'] if p['active']]
        self.assertEqual(activos, ['month'])
        html = response.content.decode()
        marca = html.index('data-period="month"')
        mes = html[html.rindex('<a', 0, marca):html.index('>', marca)]
        self.assertIn('active', mes)
        self.assertEqual(html.count('aria-current="true"'), 1)

    def test_parcial_y_pagina_completa_comparten_los_datos_del_grafico(self):
        params = {'start': '2026-01-01', 'end': '2026-12-31'}
        full = self.client.get(self.url, params)
        partial = self.client.get(self.url, params, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(
            full.context['financial_chart']['buckets'],
            partial.context['financial_chart']['buckets'],
        )
        self.assertEqual(
            full.context['financial_chart']['totals'],
            partial.context['financial_chart']['totals'],
        )
        self.assertIn(partial.content.decode().strip()[:200], full.content.decode())

    def test_sin_marca_la_pagina_completa_sigue_igual(self):
        response = self.client.get(self.url)
        html = response.content.decode()

        self.assertTemplateUsed(response, 'case_manager/gestor/dashboard.html')
        self.assertIn('<html', html)
        self.assertIn('Próximos pagos', html)
        self.assertIn('data-financial-panel', html)
        self.assertIn('X-Requested-With', response.headers['Vary'])

    def test_parcial_sin_sesion_redirige_al_login(self):
        self.client.logout()
        response = self.client.get(self.url, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('data-financial-chart', response.content.decode())

    def test_tabla_de_proximos_pagos_vacia_tiene_columnas_validas(self):
        respuesta = self.client.get(self.url)
        html = respuesta.content.decode()
        inicio = html.index('id="tablaProximosPagos"')
        fin = html.index('</table>', inicio)
        tabla = html[inicio:fin]

        self.assertNotIn('colspan=', tabla)
        self.assertIn('<tbody></tbody>', tabla.replace('\n', '').replace(' ', ''))

    def test_el_deudor_sale_en_su_lista_y_no_en_la_otra(self):
        respuesta = self.client.get(self.url)

        deudores = [f.case.client.full_name for f in respuesta.context['debtors']]
        expectativas = [
            f.case.client.full_name for f in respuesta.context['expectations']
        ]

        self.assertIn('Deudor Uno', deudores)
        self.assertNotIn('Deudor Uno', expectativas)

    def test_la_expectativa_sale_en_su_lista_y_no_en_la_otra(self):
        """
        Es la confusion que mas caro sale: una expectativa no se puede cobrar.
        """
        respuesta = self.client.get(self.url)

        deudores = [f.case.client.full_name for f in respuesta.context['debtors']]
        expectativas = [
            f.case.client.full_name for f in respuesta.context['expectations']
        ]

        self.assertIn('Expectativa Dos', expectativas)
        self.assertNotIn('Expectativa Dos', deudores)


class ClientCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

    def test_se_puede_dar_de_alta_un_cliente(self):
        respuesta = self.client.post(
            reverse('case_manager:gestor_client_create'),
            {
                'identification': '16.484.186',
                'full_name': 'Carlos Emiro Giraldo',
                'email': '',
                'phone': '',
                'is_active': 'on',
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        creado = ClientModel.objects.get()
        # La cedula se guarda normalizada, porque es por donde pregunta el
        # portal.
        self.assertEqual(creado.identification, '16484186')

    def test_el_aviso_avisa_cuando_el_cliente_no_tiene_correo(self):
        """
        Sin correo no hay a donde mandar el codigo, y el cliente se encontrara
        el portal cerrado sin saber por que. Mejor decirlo ahora, cuando quien
        puede arreglarlo esta delante.
        """
        respuesta = self.client.post(
            reverse('case_manager:gestor_client_create'),
            {
                'identification': '16484186',
                'full_name': 'Carlos Giraldo',
                'email': '',
                'phone': '',
                'is_active': 'on',
            },
            follow=True,
        )

        self.assertContains(respuesta, 'cannot use the portal')

    def test_con_correo_el_aviso_dice_a_donde_ira_el_codigo(self):
        respuesta = self.client.post(
            reverse('case_manager:gestor_client_create'),
            {
                'identification': '16484187',
                'full_name': 'Ana Giraldo',
                'email': 'ana@example.test',
                'phone': '',
                'is_active': 'on',
            },
            follow=True,
        )

        self.assertContains(respuesta, 'ana@example.test')

    def test_una_cedula_sin_digitos_no_pasa(self):
        respuesta = self.client.post(
            reverse('case_manager:gestor_client_create'),
            {'identification': 'abc', 'full_name': 'Nadie',
             'email': '', 'phone': '', 'is_active': 'on'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(ClientModel.objects.exists())

    def test_se_puede_editar_un_cliente(self):
        cliente = ClientModel.objects.create(
            identification='16484186', full_name='Nombre Viejo',
            email='cliente16484186@example.test'
        )

        self.client.post(
            reverse('case_manager:gestor_client_update', args=[cliente.pk]),
            {'identification': '16484186', 'full_name': 'Nombre Nuevo',
             'email': '', 'phone': '', 'is_active': 'on'},
        )

        cliente.refresh_from_db()
        self.assertEqual(cliente.full_name, 'Nombre Nuevo')

    def test_el_listado_busca_por_nombre_y_por_cedula(self):
        ClientModel.objects.create(identification='111', full_name='Ana Perez', email='cliente111@example.test')
        ClientModel.objects.create(identification='222', full_name='Luis Gomez', email='cliente222@example.test')

        url = reverse('case_manager:gestor_client_list')

        por_nombre = self.client.get(url, {'q': 'Ana'})
        self.assertEqual(len(por_nombre.context['clients']), 1)

        por_cedula = self.client.get(url, {'q': '222'})
        self.assertEqual(len(por_cedula.context['clients']), 1)
        self.assertEqual(
            por_cedula.context['clients'][0].full_name, 'Luis Gomez'
        )


class CaseCrudTests(TestCase):
    """
    El asunto y su dinero, que se guardan juntos o no se guardan.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cls.cliente = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test'
        )

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

    def datos(self, **cambios):
        datos = {
            'client': str(self.cliente.pk),
            'service': Service.JUDICIAL,
            'procedure': Procedure.ORDINARY,
            'area': '',
            'subtype': '',
            'second_subtype': '',
            'stage': str(Stage.IN_PROGRESS),
            'instance': 'Primera instancia',
            'is_active': 'on',
            'case_number': '2026-00145-00',
            'court': Court.CIRCUIT,
            'city': 'Armenia',
            'sector': '',
            'entity': '',
            'administrative_case_number': '',
            'administrative_city': '',
            'police_instance': '',
            'police_office': '',
            'police_case_number': '',
            'police_city': '',
            'paz_y_salvo_authorized': '',
            # El formset del dinero.
            'finance-TOTAL_FORMS': '1',
            'finance-INITIAL_FORMS': '0',
            'finance-MIN_NUM_FORMS': '0',
            'finance-MAX_NUM_FORMS': '1',
            'finance-0-start_date': '',
            'finance-0-mandate': Mandate.PAYMENT,
            'finance-0-contingency_percentage': '0',
            'finance-0-contingency_value': '0',
            'finance-0-agreed_fee': '6000000',
            'finance-0-paid_amount': '2000000',
            'finance-0-show_in_dashboard': 'on',
        }
        datos.update(cambios)
        return datos

    def test_se_guardan_el_asunto_y_su_dinero_de_una_vez(self):
        respuesta = self.client.post(
            reverse('case_manager:gestor_case_create'), self.datos()
        )

        self.assertEqual(respuesta.status_code, 302)
        caso = CaseModel.objects.get()
        self.assertEqual(caso.case_number, '2026-00145-00')
        self.assertEqual(caso.finance.balance, 4_000_000)

    def test_el_formulario_de_edicion_encadena_las_secciones_y_avisa_de_cambios(self):
        caso = CaseModel.objects.create(client=self.cliente, service=Service.JUDICIAL)
        html = self.client.get(reverse('case_manager:gestor_case_update', args=[caso.pk])).content.decode()

        # Asunto -> pagos -> paz y salvo/avisos -> notas: cada una menos la ultima con su siguiente.
        for marker in ('data-case-overview', 'data-payment-main', 'data-payment-followups', 'aria-label="Notas y avisos"'):
            self.assertRegex(html, r'<section[^>]*' + marker + r'[^>]*data-gestor-section|<section[^>]*data-gestor-section[^>]*' + marker)
        self.assertEqual(html.count('<section'), html.count('data-gestor-section'))
        self.assertLess(html.index('data-payment-main'), html.index('data-payment-followups'))
        self.assertLess(html.index('data-payment-followups'), html.index('aria-label="Notas y avisos"'))
        self.assertIn('gestor-next-section', html)
        self.assertIn('id="cambiosSinGuardar"', html)
        self.assertIn('data-unsaved-continue', html)
        self.assertIn('data-unsaved-save', html)
        self.assertIn('data-unsaved-guard', html)
        self.assertGreaterEqual(html.count('data-money'), 4)  # 3 importes + el de cada pago

    def test_los_importes_limpios_se_siguen_guardando_igual(self):
        respuesta = self.client.post(
            reverse('case_manager:gestor_case_create'),
            self.datos(**{'finance-0-agreed_fee': '9000000000000', 'finance-0-paid_amount': '1234567'}),
        )
        self.assertEqual(respuesta.status_code, 302)
        finanzas = CaseModel.objects.get().finance
        self.assertEqual((finanzas.agreed_fee, finanzas.paid_amount), (9_000_000_000_000, 1_234_567))

    def test_payment_history_round_trips_and_drives_totals(self):
        rows = [
            {'kind': 'administrative', 'amount': 100000, 'date': '2026-09-01', 'next_date': '2026-09-10'},
            {'kind': 'payment', 'amount': 900000, 'date': '2026-09-10', 'next_date': '2026-10-10'},
            {'kind': 'payment', 'amount': 2000000, 'date': '2026-10-10', 'next_date': ''},
        ]
        response = self.client.post(reverse('case_manager:gestor_case_create'), self.datos(**{
            'finance-0-payment_history': json.dumps(rows),
            'finance-0-paid_amount': '99999999',
        }))
        self.assertEqual(response.status_code, 302)
        case = CaseModel.objects.get()
        self.assertEqual(case.finance.paid_amount, 3000000)
        self.assertEqual(case.finance.balance, 3000000)
        self.assertEqual(CaseFinanceModel.objects.totals()['paid'], 3000000)
        response = self.client.get(reverse('case_manager:gestor_case_update', args=[case.pk]))
        self.assertContains(response, '2026-10-10')
        self.assertContains(response, '2000000')
        self.assertEqual(len(case.finance.payment_history), 3)

    def test_expected_payment_roundtrip_dashboard_and_receipt(self):
        rows = [
            {'kind': 'payment', 'amount': 100000, 'date': ''},
            {'kind': 'expected', 'amount': 900000, 'date': ''},
            {'kind': 'expected', 'amount': 500000, 'date': '2026-12-01'},
        ]
        response = self.client.post(reverse('case_manager:gestor_case_create'),
                                    self.datos(**{'finance-0-payment_history': json.dumps(rows)}))
        self.assertEqual(response.status_code, 302)
        case = CaseModel.objects.get()
        self.assertEqual(case.finance.paid_amount, 100000)
        self.assertEqual(case.finance.balance, 5900000)
        edit = self.client.get(reverse('case_manager:gestor_case_update', args=[case.pk]))
        self.assertContains(edit, 'value="expected" selected', count=2)
        dashboard = self.client.get(reverse('case_manager:gestor_dashboard'))
        self.assertEqual(dashboard.context['upcoming_total'], 1400000)
        self.assertEqual(dashboard.context['upcoming_payments'][0]['date'], '2026-12-01')
        self.assertContains(dashboard, 'Sin fecha definida')
        rows[1]['kind'] = 'payment'
        response = self.client.post(reverse('case_manager:gestor_case_update', args=[case.pk]),
            self.datos(**{'finance-INITIAL_FORMS': '1', 'finance-0-id': str(case.finance.pk), 'finance-0-case': str(case.pk),
                          'finance-0-payment_history': json.dumps(rows)}))
        self.assertEqual(response.status_code, 302)
        case.finance.refresh_from_db()
        self.assertEqual(case.finance.paid_amount, 1000000)
        dashboard = self.client.get(reverse('case_manager:gestor_dashboard'))
        self.assertEqual(dashboard.context['upcoming_total'], 500000)
        case.finance.show_in_dashboard = False
        case.finance.save()
        dashboard = self.client.get(reverse('case_manager:gestor_dashboard'))
        self.assertEqual(dashboard.context['upcoming_total'], 0)

    def test_invalid_expected_payment_is_rejected(self):
        for row in [
            {'kind': 'expected', 'amount': 0},
            {'kind': 'expected', 'amount': -1},
            {'kind': 'expected', 'amount': 10, 'date': 'invalid'},
        ]:
            with self.subTest(row=row):
                response = self.client.post(reverse('case_manager:gestor_case_create'),
                    self.datos(**{'finance-0-payment_history': json.dumps([row])}))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['finance_formset'].errors[0]['payment_history'])
                self.assertFalse(CaseModel.objects.exists())

    def test_un_abono_sin_fecha_se_guarda(self):
        """
        Ningun campo del pago es obligatorio.

        Un abono se registra muchas veces antes de tener el comprobante
        delante --el cliente avisa por telefono y el papel llega dias
        despues--, y obligar a inventarse una fecha para poder guardar el
        importe es peor que guardarlo sin ella: la inventada parece un dato y
        la que falta se ve que falta.
        """
        respuesta = self.client.post(
            reverse('case_manager:gestor_case_create'),
            self.datos(**{'finance-0-payment_history': json.dumps(
                [{'kind': 'payment', 'amount': 50000, 'date': '', 'next_date': ''}]
            )}),
        )

        self.assertEqual(respuesta.status_code, 302)
        caso = CaseModel.objects.get()
        self.assertEqual(caso.finance.paid_amount, 50000)
        self.assertEqual(caso.finance.payment_history[0]['date'], '')

    def test_invalid_payment_dates_do_not_save_case_or_finance(self):
        for row in (
            {'kind': 'payment', 'amount': 50000, 'date': '2026-09-10', 'next_date': '2026-09-01'},
            {'kind': 'payment', 'amount': -1, 'date': '2026-09-10'},
        ):
            with self.subTest(row=row):
                response = self.client.post(reverse('case_manager:gestor_case_create'), self.datos(**{
                    'finance-0-payment_history': json.dumps([row]),
                }))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['finance_formset'].errors[0]['payment_history'])
                self.assertFalse(CaseModel.objects.exists())
                # Y ya no se pinta la franja de arriba: los errores que no son
                # de un campo salen flotando, donde quien acaba de darle a
                # guardar los ve sin subir.
                self.assertNotContains(response, 'alert alert-danger')

    def test_old_payment_without_date_is_preserved(self):
        self.client.post(reverse('case_manager:gestor_case_create'), self.datos())
        case = CaseModel.objects.get()
        from ..forms import CaseFinanceForm
        rows = CaseFinanceForm(instance=case.finance).payment_rows
        response = self.client.post(reverse('case_manager:gestor_case_update', args=[case.pk]), self.datos(**{
            'finance-INITIAL_FORMS': '1', 'finance-0-id': str(case.finance.pk),
            'finance-0-case': str(case.pk), 'finance-0-payment_history': json.dumps(rows),
        }))
        self.assertEqual(response.status_code, 302)
        case.finance.refresh_from_db()
        self.assertEqual(case.finance.paid_amount, 2000000)
        self.assertTrue(case.finance.payment_history[1]['legacy'])

    def test_si_el_dinero_no_vale_no_se_guarda_nada(self):
        """
        La regla del modelo: una cuota litis no lleva honorario pactado. Si el
        asunto se guardara igual, quedaria sin modalidad y sin sumar en ningun
        panel, y nadie sabria que esta a medias.
        """
        respuesta = self.client.post(
            reverse('case_manager:gestor_case_create'),
            self.datos(**{
                'finance-0-mandate': Mandate.CONTINGENCY,
                'finance-0-agreed_fee': '6000000',
            }),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(CaseModel.objects.exists())
        self.assertFalse(CaseFinanceModel.objects.exists())

    def test_si_el_asunto_no_vale_no_se_guarda_el_dinero(self):
        """Una etapa que no es de ese servicio la rechaza `CaseModel.clean()`."""
        respuesta = self.client.post(
            reverse('case_manager:gestor_case_create'),
            self.datos(instance='Una instancia inventada'),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(CaseModel.objects.exists())
        self.assertFalse(CaseFinanceModel.objects.exists())

    def test_se_puede_editar_un_asunto_y_su_dinero(self):
        self.client.post(
            reverse('case_manager:gestor_case_create'), self.datos()
        )
        caso = CaseModel.objects.get()

        self.client.post(
            reverse('case_manager:gestor_case_update', args=[caso.pk]),
            self.datos(**{
                'finance-INITIAL_FORMS': '1',
                'finance-0-id': str(caso.finance.pk),
                'finance-0-case': str(caso.pk),
                'finance-0-paid_amount': '6000000',
            }),
        )

        caso.refresh_from_db()
        self.assertEqual(caso.finance.balance, 0)
        # Y no se ha duplicado la fila del dinero.
        self.assertEqual(CaseFinanceModel.objects.count(), 1)


class SettlementToggleTests(TestCase):
    """El interruptor del paz y salvo, desde el listado."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cliente = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test'
        )
        cls.case = CaseModel.objects.create(
            client=cliente, service=Service.JUDICIAL, stage=Stage.FINISHED
        )
        cls.url = reverse(
            'case_manager:gestor_case_toggle_settlement', args=[cls.case.pk]
        )

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

    def test_autoriza_y_retira(self):
        self.client.post(self.url)
        self.case.refresh_from_db()
        self.assertTrue(self.case.paz_y_salvo_authorized)

        self.client.post(self.url)
        self.case.refresh_from_db()
        self.assertFalse(self.case.paz_y_salvo_authorized)

    def test_un_get_no_cambia_nada(self):
        """
        Cambia un dato, asi que es `POST`. Un `GET` que cambia datos lo
        dispara cualquier cosa que siga enlaces: un prefetch, un antivirus,
        un rastreador.
        """
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 405)
        self.case.refresh_from_db()
        self.assertFalse(self.case.paz_y_salvo_authorized)

    def test_sin_el_grupo_no_se_puede(self):
        self.client.logout()
        make_user('cliente')
        login_as(self.client, 'cliente')

        self.client.post(self.url)

        self.case.refresh_from_db()
        self.assertFalse(self.case.paz_y_salvo_authorized)

    def test_autorizar_aqui_lo_ensena_en_el_portal(self):
        """
        Las dos mitades hablan del mismo dato: lo que el despacho enciende
        aqui es lo que el cliente ve alli.
        """
        self.client.post(self.url)
        self.client.logout()

        respuesta = identificarse(self.client)

        self.assertContains(
            respuesta,
            reverse('case_manager:paz_y_salvo', args=[self.case.pk]),
        )


class ClientToCasesTests(TestCase):
    """
    Ir de un cliente a sus asuntos.

    Sin esto hay que salir al otro listado y buscarlo a mano, que es lo que
    se hace veinte veces al dia.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())

        cls.ana = ClientModel.objects.create(
            identification='1001', full_name='Ana Perez',
            email='cliente1001@example.test'
        )
        cls.luis = ClientModel.objects.create(
            identification='1002', full_name='Luis Gomez',
            email='cliente1002@example.test'
        )
        cls.de_ana = CaseModel.objects.create(
            client=cls.ana, service=Service.JUDICIAL, stage=Stage.IN_PROGRESS
        )
        CaseModel.objects.create(
            client=cls.luis, service=Service.CONCILIATION,
            stage=Stage.UNDER_REVIEW,
        )
        cls.url = reverse('case_manager:gestor_case_list')

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

    def test_el_listado_de_clientes_enlaza_a_sus_asuntos(self):
        respuesta = self.client.get(
            reverse('case_manager:gestor_client_list')
        )

        self.assertContains(respuesta, f'{self.url}?cliente={self.ana.pk}')

    def test_acotar_por_cliente_deja_solo_los_suyos(self):
        respuesta = self.client.get(self.url, {'cliente': str(self.ana.pk)})

        self.assertEqual(list(respuesta.context['cases']), [self.de_ana])
        self.assertEqual(respuesta.context['cliente'], self.ana)

    def test_un_cliente_que_no_existe_no_revienta(self):
        """
        Un enlace viejo o mal copiado ensena la lista entera, no un 500.
        """
        import uuid

        respuesta = self.client.get(self.url, {'cliente': str(uuid.uuid4())})

        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.context['cliente'])
        self.assertEqual(len(respuesta.context['cases']), 2)

    def test_un_cliente_que_ni_siquiera_es_un_uuid_tampoco(self):
        respuesta = self.client.get(self.url, {'cliente': 'esto-no-es-un-uuid'})

        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.context['cliente'])

    def test_buscar_dentro_de_un_cliente_no_saca_los_de_otro(self):
        """
        El filtro sobrevive a la busqueda. Sin esto, buscar dentro de los
        asuntos de alguien devuelve los de todo el mundo.
        """
        respuesta = self.client.get(
            self.url, {'cliente': str(self.ana.pk), 'q': 'o'}
        )

        for caso in respuesta.context['cases']:
            self.assertEqual(caso.client, self.ana)

    def test_el_alta_llega_con_el_cliente_puesto(self):
        respuesta = self.client.get(
            reverse('case_manager:gestor_case_create'),
            {'cliente': str(self.ana.pk)},
        )

        self.assertEqual(
            respuesta.context['form'].initial.get('client'), str(self.ana.pk)
        )

    def test_el_alta_sin_cliente_no_preselecciona_nada(self):
        respuesta = self.client.get(reverse('case_manager:gestor_case_create'))

        self.assertIsNone(respuesta.context['form'].initial.get('client'))


class ListadosAlturaTests(TestCase):
    def test_los_dos_listados_reservan_55vh_de_cuerpo(self):
        css = (Path(settings.BASE_DIR) / 'public/staticfiles/assets/custom/css/gestor.css').read_text(encoding='utf-8')
        for table in ('tablaAsuntos', 'tablaClientes'):
            self.assertRegex(css, r'#%s[^{]*\{[^}]*min-height: 55vh' % table)
        self.assertNotIn('tablaDeudores', css)


class TablasTests(TestCase):
    """
    Los listados largos, ahora que los pagina el navegador.

    Antes esto probaba la paginacion del servidor, y una de las pruebas
    nacio de un 500 de produccion: el enlace «anterior» de la primera pagina
    llamaba a `page_obj.previous_page_number`, que en la primera pagina lanza
    `EmptyPage`. Ese codigo ya no existe --las vistas no paginan--, asi que
    lo que se comprueba es lo que lo sustituye: que las filas llegan
    **todas**, porque DataTables ordena y busca sobre lo que hay en el HTML,
    y que la tabla trae el enganche y los guiones que la arrancan.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cls.user = make_user('gestora_tablas', gestor=True)
        for numero in range(30):
            ClientModel.objects.create(
                identification=f'9000{numero:04d}',
                full_name=f'Cliente {numero:02d}',
            )

    def setUp(self):
        login_as(self.client, 'gestora_tablas')

    def test_el_listado_trae_todas_las_filas(self):
        """
        Sin esto, DataTables ordenaria veinticinco filas y diria que eso es
        el orden de los treinta.
        """
        respuesta = self.client.get(reverse('case_manager:gestor_client_list'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context['clients']), 30)
        # `ListView` deja la clave puesta aunque no pagine; lo que importa es
        # que venga vacia, que es lo que dice que no se partio la lista.
        self.assertIsNone(respuesta.context['page_obj'])
        self.assertFalse(respuesta.context['is_paginated'])

    def test_la_tabla_lleva_el_enganche_y_los_guiones(self):
        respuesta = self.client.get(reverse('case_manager:gestor_client_list'))

        self.assertContains(respuesta, 'data-datatable')
        self.assertContains(respuesta, 'datatables.min.js')
        self.assertContains(respuesta, 'pdfmake.min.js')
        self.assertContains(respuesta, 'gestor_tables.js')
        self.assertContains(respuesta, 'dt-i18n')

    def test_la_columna_de_acciones_no_se_ordena(self):
        """
        Son botones. Ordenar por una columna de botones no significa nada, y
        el `<th>` es quien lo dice para no tener que renumerar indices cada
        vez que alguien mete una columna en medio.
        """
        respuesta = self.client.get(reverse('case_manager:gestor_client_list'))

        self.assertContains(respuesta, 'data-dt-no-sort')

    def test_la_lista_de_clientes_sale_ordenada(self):
        """
        `annotate` agrupa, y una consulta agrupada deja de estar ordenada
        aunque el `Meta` lo diga. Sigue importando sin paginacion: es el
        orden que ve quien entra antes de tocar ninguna cabecera.
        """
        clientes = self.client.get(
            reverse('case_manager:gestor_client_list')
        ).context['clients']

        self.assertTrue(clientes.ordered)
        self.assertEqual(
            [c.full_name for c in clientes],
            sorted(c.full_name for c in clientes),
        )

    def test_el_filtro_de_la_direccion_se_sigue_respetando(self):
        """Un enlace guardado con `?q=` no se rompe por quitar el buscador."""
        respuesta = self.client.get(
            reverse('case_manager:gestor_client_list'), {'q': 'Cliente 0'}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context['clients']), 10)
        self.assertContains(respuesta, 'Show all')

    def test_los_asuntos_tambien(self):
        respuesta = self.client.get(reverse('case_manager:gestor_case_list'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-datatable')
        self.assertFalse(respuesta.context['is_paginated'])


class TablasVaciasTests(TestCase):
    """
    DataTables no admite filas con `colspan` en el tbody: con la tabla vacia
    avisa «Requested unknown parameter '1' for row 0, column 1». El texto de
    tabla vacia viaja en `data-dt-empty` y lo pinta DataTables; sin JS, un
    `<p data-dt-fallback>` tras la tabla dice lo mismo.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        make_user('gestora_vacia', gestor=True)

    def setUp(self):
        login_as(self.client, 'gestora_vacia')

    def _tablas(self, url):
        import re
        html = self.client.get(url).content.decode()
        tablas = re.findall(r'<table\b[^>]*\bdata-datatable\b[^>]*>.*?</table>', html, re.S)
        self.assertTrue(tablas, url)
        return html, tablas

    def test_ninguna_tabla_vacia_tiene_colspan_y_todas_llevan_su_texto(self):
        urls = {
            'dashboard': reverse('case_manager:gestor_dashboard'),
            'clientes': reverse('case_manager:gestor_client_list'),
            'asuntos': reverse('case_manager:gestor_case_list'),
            'ficha': None,
        }
        # La ficha necesita un cliente; se crea al llegar a ella para no
        # ensuciar el listado de clientes, que tambien debe verse vacio.
        for nombre, url in urls.items():
            with self.subTest(nombre):
                if nombre == 'ficha':
                    cliente = ClientModel.objects.create(
                        identification='800000001', full_name='Cliente sin asuntos',
                    )
                    url = reverse('case_manager:gestor_client_detail', args=[cliente.pk])
                html, tablas = self._tablas(url)
                for tabla in tablas:
                    self.assertNotIn('colspan', tabla)
                    self.assertRegex(tabla, r'<table\b[^>]*\bdata-dt-empty="[^"]+"')
                    self.assertRegex(tabla, r'<tbody>\s*</tbody>')
                self.assertEqual(html.count('data-dt-fallback'), len(tablas))

    def test_el_dashboard_tiene_sus_tres_tablas_del_panel(self):
        _, tablas = self._tablas(reverse('case_manager:gestor_dashboard'))
        ids = ''.join(tablas)
        for tabla_id in ('tablaProximosPagos', 'tablaDeudores', 'tablaExpectativas'):
            self.assertIn(tabla_id, ids)

    def test_el_guion_usa_el_texto_de_cada_tabla_como_tabla_vacia(self):
        js = (Path(settings.BASE_DIR) / 'public/staticfiles/assets/custom/js/gestor_tables.js').read_text(encoding='utf-8')
        self.assertIn('dataset.dtEmpty', js)
        self.assertIn('emptyTable', js)

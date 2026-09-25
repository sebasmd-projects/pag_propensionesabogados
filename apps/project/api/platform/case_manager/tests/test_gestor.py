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
import json

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

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

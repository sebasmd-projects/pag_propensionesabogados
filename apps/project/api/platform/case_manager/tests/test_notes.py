"""
Las novedades del expediente y los correos que las acompanan.

Un correo que sale mal no da error: llega, y llega roto --sin membrete,
respondiendo a un buzon que nadie lee, o marcado como spam--. Nadie se entera
hasta que un cliente lo dice, si lo dice. De ahi que estas pruebas miren el
mensaje por dentro: de quien viene, a donde responde, que partes lleva y como
estan enlazadas las imagenes.

La otra mitad es cuando **no** se manda: sin correo del cliente, o en una nota
interna. Las dos son normales y ninguna puede reventar el guardado.
"""

from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from ..choices import Court, Mandate, NoteKind, Procedure, Service, Stage
from ..emails import REPLY_TO, send_case_note
from ..models import CaseModel, CaseNoteModel, ClientModel
from .test_access import make_user

CLAVE = 'una-contrasena-larga-de-verdad'


def make_case(*, email='cliente@ejemplo.com', identification='16484186'):
    cliente = ClientModel.objects.create(
        identification=identification,
        full_name='Carlos Emiro Giraldo',
        email=email,
    )
    return CaseModel.objects.create(
        client=cliente,
        service=Service.JUDICIAL,
        procedure=Procedure.ORDINARY,
        stage=Stage.IN_PROGRESS,
        instance='Primera instancia',
        case_number='2026-00145-00',
        court=Court.CIRCUIT,
    )


class NoteModelTests(TestCase):
    """Lo que decide como se ve y que se hace con cada nota."""

    @classmethod
    def setUpTestData(cls):
        cls.case = make_case()

    def test_solo_la_de_documento_pide_algo_al_cliente(self):
        """
        Es la unica que exige una accion suya, y por eso el portal y el correo
        la destacan. Si todas pidieran lo mismo, ninguna destacaria.
        """
        for kind, espera_accion in [
            (NoteKind.DOCUMENT, True),
            (NoteKind.INFO, False),
            (NoteKind.BLOCKED, False),
            (NoteKind.STAGE, False),
        ]:
            with self.subTest(kind=kind):
                nota = CaseNoteModel(case=self.case, kind=kind, title='x', body='y')
                self.assertEqual(nota.needs_client_action, espera_accion)

    def test_cada_tipo_tiene_color_e_icono(self):
        """
        El color solo no distingue --el ambar de «en espera» y el rojo de
        «falta un documento» se parecen con una deficiencia de vision del
        color--, asi que cada tipo lleva tambien su icono.
        """
        iconos, colores = set(), set()
        for kind, _label in NoteKind.choices:
            estilo = CaseNoteModel(case=self.case, kind=kind).style
            iconos.add(estilo['icon'])
            colores.add(estilo['tone'])

        self.assertEqual(len(iconos), len(NoteKind.choices))
        self.assertEqual(len(colores), len(NoteKind.choices))

    def test_una_nota_interna_no_sale_en_el_portal(self):
        CaseNoteModel.objects.create(
            case=self.case, title='Para el expediente', body='...',
            visible_to_client=False,
        )
        CaseNoteModel.objects.create(
            case=self.case, title='Para el cliente', body='...',
        )

        visibles = [n.title for n in self.case.notes.for_client()]

        self.assertEqual(visibles, ['Para el cliente'])

    def test_lo_que_pide_algo_va_primero_aunque_sea_lo_mas_viejo(self):
        """
        Una peticion de documento por debajo de tres avisos es una peticion
        que no se atiende, y ese es justo el caso en el que el asunto se queda
        parado esperando al cliente.
        """
        CaseNoteModel.objects.create(
            case=self.case, kind=NoteKind.DOCUMENT,
            title='Falta la cédula', body='...',
        )
        for i in range(3):
            CaseNoteModel.objects.create(
                case=self.case, kind=NoteKind.INFO,
                title=f'Aviso {i}', body='...',
            )

        primera = self.case.notes.for_client().first()

        self.assertEqual(primera.title, 'Falta la cédula')


class EmailShapeTests(TestCase):
    """
    Como sale el correo por dentro.

    Es lo que nadie mira hasta que falla, y cuando falla no avisa.
    """

    def setUp(self):
        mail.outbox = []
        self.case = make_case()
        self.nota = CaseNoteModel.objects.create(
            case=self.case,
            kind=NoteKind.DOCUMENT,
            title='Falta su cédula ampliada',
            body='Necesitamos copia de la cédula al 150 %.',
        )

    def _enviar(self):
        self.assertTrue(send_case_note(self.nota))
        self.assertEqual(len(mail.outbox), 1)
        return mail.outbox[0]

    # --- de quien viene y a donde se responde ----------------------------
    @override_settings(DEFAULT_FROM_EMAIL='no-reply@propensionesabogados.com')
    def test_sale_del_buzon_configurado_en_django(self):
        """
        Del `DEFAULT_FROM_EMAIL`, que es el que de verdad esta autorizado a
        enviar por el dominio. Poner otro en el `From` hace que el envio falle
        la autenticacion y acabe en spam.
        """
        self.assertEqual(
            self._enviar().from_email, 'no-reply@propensionesabogados.com'
        )

    def test_se_responde_a_direccion(self):
        """Quien firma el envio no es quien atiende la respuesta."""
        mensaje = self._enviar()

        self.assertEqual(mensaje.reply_to, [REPLY_TO])
        self.assertEqual(REPLY_TO, 'director@propensionesabogados.com')

    def test_va_al_correo_del_cliente_y_a_nadie_mas(self):
        mensaje = self._enviar()

        self.assertEqual(mensaje.to, ['cliente@ejemplo.com'])
        self.assertFalse(mensaje.cc)
        self.assertFalse(mensaje.bcc)

    # --- las dos versiones -----------------------------------------------
    def test_lleva_html_y_texto_plano(self):
        """
        Un correo solo-HTML puntua peor en los filtros de spam, y hay quien
        lee el correo en texto.
        """
        mensaje = self._enviar()

        self.assertTrue(mensaje.body.strip())
        tipos = [tipo for _contenido, tipo in mensaje.alternatives]
        self.assertIn('text/html', tipos)

    def test_el_texto_plano_no_lleva_etiquetas(self):
        self.assertNotIn('<table', self._enviar().body)

    def test_el_cuerpo_de_la_nota_esta_en_los_dos(self):
        mensaje = self._enviar()
        html = mensaje.alternatives[0][0]

        self.assertIn('cédula al 150', mensaje.body)
        self.assertIn('cédula al 150', html)

    # --- las imagenes, que es lo que se bloquea --------------------------
    def test_las_imagenes_viajan_dentro_del_mensaje(self):
        """
        Enlazadas se bloquean: casi todos los clientes de correo no cargan
        imagenes remotas por defecto, y el membrete sale como un cuadro roto.
        """
        mensaje = self._enviar()

        adjuntas = [
            p for p in mensaje.attachments
            if getattr(p, 'get_content_maintype', lambda: '')() == 'image'
        ]

        self.assertEqual(len(adjuntas), 2)

    def test_cada_imagen_lleva_su_content_id_entre_angulos(self):
        """
        Sin los `<>` hay clientes que no resuelven el `cid:` y ensenan el
        cuadro roto igual. Lo pide el RFC 2392.
        """
        mensaje = self._enviar()

        ids = {
            p['Content-ID'] for p in mensaje.attachments
            if getattr(p, 'get_content_maintype', lambda: '')() == 'image'
        }

        self.assertEqual(ids, {'<membrete>', '<firma>'})

    def test_las_imagenes_van_como_inline_y_no_como_adjuntos(self):
        """
        Sin esto, el cliente de correo ensena el membrete y la firma como dos
        ficheros al final del mensaje.
        """
        mensaje = self._enviar()

        for parte in mensaje.attachments:
            if getattr(parte, 'get_content_maintype', lambda: '')() == 'image':
                self.assertEqual(
                    parte['Content-Disposition'].split(';')[0], 'inline'
                )

    def test_el_html_referencia_esos_mismos_cid(self):
        """
        Las dos mitades tienen que hablar de lo mismo: un `cid` en la
        plantilla que no se adjunte es un cuadro roto, y al reves es peso de
        mas.
        """
        html = self._enviar().alternatives[0][0]

        self.assertIn('src="cid:membrete"', html)
        self.assertIn('src="cid:firma"', html)
        self.assertNotIn('src="http', html)

    def test_el_mensaje_se_arma_como_related(self):
        """
        `related` le dice al cliente de correo que los adjuntos son partes del
        HTML y no ficheros sueltos.
        """
        self.assertEqual(self._enviar().mixed_subtype, 'related')

    # --- el contenido -----------------------------------------------------
    def test_el_asunto_dice_de_que_va(self):
        asunto = self._enviar().subject

        self.assertIn(str(NoteKind.DOCUMENT.label), asunto)

    def test_lleva_los_datos_del_asunto_pero_no_el_dinero(self):
        """
        El expediente es del cliente; lo que se le cobra es de puertas
        adentro, y un correo se reenvia mas facil que una pagina.
        """
        from ..models import CaseFinanceModel

        CaseFinanceModel.objects.create(
            case=self.case, mandate=Mandate.PAYMENT,
            agreed_fee=6_000_000, paid_amount=2_000_000,
        )

        html = self._enviar().alternatives[0][0]

        self.assertIn('2026-00145-00', html)
        self.assertNotIn('6000000', html)
        self.assertNotIn('6.000.000', html)


class EmailNotSentTests(TestCase):
    """Cuando no se manda, que es tan importante como cuando si."""

    def setUp(self):
        mail.outbox = []

    def test_sin_correo_del_cliente_no_se_manda_ni_revienta(self):
        """Hay clientes de los que solo se tiene el telefono."""
        case = make_case(email='')
        nota = CaseNoteModel.objects.create(
            case=case, title='Novedad', body='...'
        )

        self.assertFalse(send_case_note(nota))
        self.assertEqual(len(mail.outbox), 0)

    def test_una_nota_interna_no_se_manda(self):
        case = make_case()
        nota = CaseNoteModel.objects.create(
            case=case, title='Para el expediente', body='...',
            visible_to_client=False,
        )

        self.assertFalse(send_case_note(nota))
        self.assertEqual(len(mail.outbox), 0)

    def test_notified_at_solo_se_marca_si_el_correo_salio(self):
        """
        Si se marcara antes, un fallo del servidor dejaria el expediente
        diciendo que se aviso a alguien a quien no se aviso. Eso es peor que
        no haber avisado.
        """
        case = make_case(email='')
        nota = CaseNoteModel.objects.create(
            case=case, title='Novedad', body='...'
        )

        send_case_note(nota)
        nota.refresh_from_db()

        self.assertIsNone(nota.notified_at)

    def test_cuando_sale_queda_la_fecha(self):
        """
        Es una fecha y no un booleano: «le avisamos» y «le avisamos el 3 de
        marzo» no valen lo mismo en una reclamacion.
        """
        case = make_case()
        nota = CaseNoteModel.objects.create(
            case=case, title='Novedad', body='...'
        )

        send_case_note(nota)
        nota.refresh_from_db()

        self.assertIsNotNone(nota.notified_at)


class NoteFromGestorTests(TestCase):
    """Anadir una nota desde la ficha del asunto."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cls.case = make_case()
        cls.url = reverse(
            'case_manager:gestor_case_note_create', args=[cls.case.pk]
        )

    def setUp(self):
        mail.outbox = []
        make_user('abogada', gestor=True)
        self.client.login(username='abogada', password=CLAVE)

    def datos(self, **cambios):
        datos = {
            'kind': NoteKind.DOCUMENT,
            'title': 'Falta su cédula',
            'body': 'Envíenos copia al 150 %.',
            'visible_to_client': 'on',
            'notify_client': 'on',
        }
        datos.update(cambios)
        return datos

    def test_se_guarda_y_se_manda(self):
        self.client.post(self.url, self.datos())

        nota = CaseNoteModel.objects.get()
        self.assertEqual(nota.title, 'Falta su cédula')
        self.assertEqual(len(mail.outbox), 1)

    def test_queda_quien_la_escribio(self):
        """El expediente tiene que decir quien dijo que."""
        self.client.post(self.url, self.datos())

        self.assertEqual(CaseNoteModel.objects.get().created_by.username, 'abogada')

    def test_sin_marcar_la_casilla_no_se_manda(self):
        self.client.post(self.url, self.datos(notify_client=''))

        self.assertEqual(CaseNoteModel.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_una_nota_vacia_no_se_guarda(self):
        self.client.post(self.url, self.datos(title='', body=''))

        self.assertFalse(CaseNoteModel.objects.exists())

    def test_sin_el_grupo_no_se_puede(self):
        self.client.logout()
        make_user('cliente')
        self.client.login(username='cliente', password=CLAVE)

        self.client.post(self.url, self.datos())

        self.assertFalse(CaseNoteModel.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_la_nota_llega_al_portal_del_cliente(self):
        """
        Las dos mitades hablan del mismo dato: lo que el despacho escribe aqui
        es lo que el cliente lee alli.
        """
        self.client.post(self.url, self.datos())
        self.client.logout()

        respuesta = self.client.post(
            reverse('case_manager:public_query'),
            {'identification': '16484186', 'access_key': 'C4186'},
        )

        self.assertContains(respuesta, 'Falta su cédula')

    def test_una_nota_interna_no_llega_al_portal(self):
        self.client.post(
            self.url,
            self.datos(title='Solo para el expediente', visible_to_client=''),
        )
        self.client.logout()

        respuesta = self.client.post(
            reverse('case_manager:public_query'),
            {'identification': '16484186', 'access_key': 'C4186'},
        )

        self.assertNotContains(respuesta, 'Solo para el expediente')


class StageChangeEmailTests(TestCase):
    """El aviso automatico cuando el asunto avanza."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())

    def setUp(self):
        mail.outbox = []
        self.case = make_case()
        make_user('abogada', gestor=True)
        self.client.login(username='abogada', password=CLAVE)
        self.url = reverse(
            'case_manager:gestor_case_update', args=[self.case.pk]
        )

    def datos(self, **cambios):
        datos = {
            'client': str(self.case.client.pk),
            'service': Service.JUDICIAL,
            'procedure': Procedure.ORDINARY,
            'area': '', 'subtype': '', 'second_subtype': '',
            'stage': str(Stage.IN_PROGRESS),
            'instance': 'Primera instancia',
            'is_active': 'on',
            'case_number': '2026-00145-00',
            'court': Court.CIRCUIT, 'city': '',
            'sector': '', 'entity': '',
            'administrative_case_number': '', 'administrative_city': '',
            'police_instance': '', 'police_office': '',
            'police_case_number': '', 'police_city': '',
            'paz_y_salvo_authorized': '',
            'notify_stage_change': 'on',
            'finance-TOTAL_FORMS': '1',
            'finance-INITIAL_FORMS': '0',
            'finance-MIN_NUM_FORMS': '0',
            'finance-MAX_NUM_FORMS': '1',
            'finance-0-start_date': '',
            'finance-0-mandate': Mandate.PAYMENT,
            'finance-0-contingency_percentage': '0',
            'finance-0-contingency_value': '0',
            'finance-0-agreed_fee': '0',
            'finance-0-paid_amount': '0',
            'finance-0-show_in_dashboard': 'on',
        }
        datos.update(cambios)
        return datos

    def test_al_cambiar_de_etapa_se_avisa(self):
        self.client.post(self.url, self.datos(stage=str(Stage.FINAL_STAGE)))

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Etapa final', mail.outbox[0].alternatives[0][0])

    def test_queda_la_nota_del_avance(self):
        self.client.post(self.url, self.datos(stage=str(Stage.FINAL_STAGE)))

        nota = CaseNoteModel.objects.get()
        self.assertEqual(nota.kind, NoteKind.STAGE)
        self.assertIsNotNone(nota.notified_at)

    def test_guardar_sin_tocar_la_etapa_no_avisa(self):
        """
        Un correo diciendo que el asunto avanzo cuando no ha avanzado gasta la
        confianza del siguiente, que puede ser el que si importa.
        """
        self.client.post(self.url, self.datos(instance='Segunda instancia'))

        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(CaseNoteModel.objects.exists())

    def test_sin_marcar_la_casilla_no_avisa(self):
        """
        El despacho decide cuando avisar: hay correcciones de etapa que no son
        novedades para nadie.
        """
        self.client.post(
            self.url,
            self.datos(stage=str(Stage.FINAL_STAGE), notify_stage_change=''),
        )

        self.assertEqual(len(mail.outbox), 0)

    def test_sin_correo_del_cliente_la_nota_queda_igual(self):
        """Lo que no se puede perder es la novedad; el correo es el aviso."""
        ClientModel.objects.filter(pk=self.case.client.pk).update(email='')

        self.client.post(self.url, self.datos(stage=str(Stage.FINAL_STAGE)))

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(CaseNoteModel.objects.count(), 1)
        self.assertIsNone(CaseNoteModel.objects.get().notified_at)

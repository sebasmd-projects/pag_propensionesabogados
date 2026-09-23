"""
El codigo de acceso del portal y su escalera de reenvios.

La escalera pedida, y la unica razon por la que existe
------------------------------------------------------
El primer envio es el que pide el cliente al consultar y no espera. Despues::

    reenvio 2         1 minuto
    reenvios 3, 4, 5  5 minutos cada uno
    tras el quinto    una hora, y el ciclo vuelve a empezar

Lo que frena no es el tanteo del codigo --de eso se ocupan el tope de
intentos y el bloqueo por IP-- sino **el envio de correos al buzon de otra
persona**. Sin escalera, quien tenga una cedula ajena puede llenarle el
buzon al titular dandole a «reenviar»; con ella, cinco correos y una hora de
silencio.

Por eso la escalera va por cliente y en la base, no por sesion ni en cache:
tirar la galleta la reiniciaria, y con varios procesos cada uno llevaria su
cuenta.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .. import portal_otp
from ..choices import Service, Stage
from ..models import CaseModel, ClientModel

CODIGO = '123456'


class LadderRulesTests(TestCase):
    """La escalera, mirada directamente y sin pasar por la pantalla."""

    def setUp(self):
        self.client_record = ClientModel.objects.create(
            identification='16484186',
            full_name='Carlos Giraldo',
            email='carlos@example.test',
        )

    def _enviar(self, veces=1, hace=None):
        """Apunta `veces` envios, el ultimo `hace` tiempo."""
        for _ in range(veces):
            portal_otp.register_send(self.client_record)

        if hace is not None:
            self.client_record.last_code_sent_at = timezone.now() - hace
            self.client_record.save(update_fields=['last_code_sent_at'])

    def test_el_primero_no_espera(self):
        self.assertTrue(portal_otp.can_send(self.client_record))

    def test_el_segundo_espera_un_minuto(self):
        self._enviar(1)

        self.assertFalse(portal_otp.can_send(self.client_record))

        self._enviar(0, hace=timedelta(seconds=61))
        self.assertTrue(portal_otp.can_send(self.client_record))

    def test_un_minuto_no_es_suficiente_a_los_cincuenta_segundos(self):
        self._enviar(1, hace=timedelta(seconds=50))

        self.assertFalse(portal_otp.can_send(self.client_record))

    def test_del_tercero_al_quinto_esperan_cinco_minutos(self):
        for enviados in (2, 3, 4):
            with self.subTest(enviados=enviados):
                self.client_record.code_sends = enviados
                self.client_record.code_blocked_until = None
                self.client_record.last_code_sent_at = (
                    timezone.now() - timedelta(minutes=4)
                )
                self.client_record.save()

                self.assertFalse(portal_otp.can_send(self.client_record))

                self.client_record.last_code_sent_at = (
                    timezone.now() - timedelta(minutes=5, seconds=1)
                )
                self.client_record.save(update_fields=['last_code_sent_at'])

                self.assertTrue(portal_otp.can_send(self.client_record))

    def test_tras_el_quinto_se_bloquea_una_hora(self):
        self._enviar(5)

        self.assertIsNotNone(self.client_record.code_blocked_until)
        self.assertFalse(portal_otp.can_send(self.client_record))

        falta = self.client_record.code_blocked_until - timezone.now()
        self.assertGreater(falta, timedelta(minutes=59))
        self.assertLessEqual(falta, timedelta(hours=1))

    def test_pasada_la_hora_el_ciclo_vuelve_a_empezar(self):
        """
        No se queda bloqueado para siempre, y tampoco reanuda donde lo dejo:
        empieza de cero, asi que el siguiente reenvio vuelve a ser de un
        minuto.
        """
        self._enviar(5)
        self.client_record.code_blocked_until = (
            timezone.now() - timedelta(seconds=1)
        )
        self.client_record.save(update_fields=['code_blocked_until'])

        self.assertTrue(portal_otp.can_send(self.client_record))

        portal_otp.register_send(self.client_record)

        self.assertEqual(self.client_record.code_sends, 1)
        self.assertIsNone(self.client_record.code_blocked_until)

    def test_acertar_el_codigo_borra_la_escalera(self):
        """
        Acertar demuestra que el buzon registrado es suyo y que lo esta
        leyendo, que es justo lo que la escalera comprobaba. Dejarsela puesta
        castigaria la proxima consulta legitima por lo que hizo esta.
        """
        self._enviar(3)

        portal_otp.reset_ladder(self.client_record)

        self.assertEqual(self.client_record.code_sends, 0)
        self.assertIsNone(self.client_record.code_blocked_until)
        self.assertTrue(portal_otp.can_send(self.client_record))

    def test_la_escalera_es_de_cada_cliente(self):
        """
        Gastarla con una cedula no puede cerrarle el portal a otra persona.
        """
        otra = ClientModel.objects.create(
            identification='77777777', full_name='Otra',
            email='otra@example.test',
        )
        self._enviar(5)

        self.assertFalse(portal_otp.can_send(self.client_record))
        self.assertTrue(portal_otp.can_send(otra))

    def test_la_escalera_sobrevive_a_recargar_el_cliente(self):
        """
        Esta en la base, no en la sesion ni en la cache. Si estuviera en la
        sesion, tirar la galleta la reiniciaria.
        """
        self._enviar(2)

        recargado = ClientModel.objects.get(pk=self.client_record.pk)

        self.assertEqual(recargado.code_sends, 2)
        self.assertFalse(portal_otp.can_send(recargado))


class LadderThroughThePortalTests(TestCase):
    """La misma escalera, pero pulsando «reenviar» en la pantalla."""

    def setUp(self):
        cache.clear()
        self.url = reverse('case_manager:public_query')
        self.client_record = ClientModel.objects.create(
            identification='16484186',
            full_name='Carlos Giraldo',
            email='carlos@example.test',
        )
        CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )

    def _pedir(self):
        with patch.object(portal_otp, 'generate_code', return_value=CODIGO):
            return self.client.post(self.url, {'identification': '16484186'})

    def _reenviar(self):
        with patch.object(portal_otp, 'generate_code', return_value=CODIGO):
            return self.client.post(self.url, {'resend': '1'})

    def _adelantar(self, tiempo):
        """Mueve hacia atras el ultimo envio, que es lo mismo que esperar."""
        self.client_record.refresh_from_db()
        self.client_record.last_code_sent_at -= tiempo
        self.client_record.save(update_fields=['last_code_sent_at'])

    def test_reenviar_antes_de_tiempo_no_manda_nada(self):
        self._pedir()
        mail.outbox.clear()

        respuesta = self._reenviar()

        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNotNone(respuesta.context['resend_at'])

    def test_la_pantalla_dice_a_que_hora_se_puede_reenviar(self):
        """
        La hora y no los segundos: el cliente puede dejar esta pantalla
        abierta un rato, y unos segundos calculados al pintarla mentirian en
        cuanto pasen.
        """
        self._pedir()
        respuesta = self._reenviar()

        esperado = portal_otp.next_send_allowed_at(
            ClientModel.objects.get(pk=self.client_record.pk)
        )
        self.assertEqual(respuesta.context['resend_at'], esperado)

    def test_pasado_el_minuto_si_manda(self):
        self._pedir()
        mail.outbox.clear()
        self._adelantar(timedelta(seconds=61))

        respuesta = self._reenviar()

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(respuesta.context['code_sent'])

    def test_cinco_envios_y_se_acabo(self):
        """El ciclo completo, tal y como se pidio."""
        self._pedir()
        self._adelantar(timedelta(seconds=61))
        self._reenviar()

        for _ in range(3):
            self._adelantar(timedelta(minutes=5, seconds=1))
            self._reenviar()

        self.assertEqual(len(mail.outbox), 5)

        self.client_record.refresh_from_db()
        self.assertIsNotNone(self.client_record.code_blocked_until)

        # Y ya no sale ni esperando cinco minutos: lo que queda es la hora.
        self._adelantar(timedelta(minutes=10))
        self._reenviar()

        self.assertEqual(len(mail.outbox), 5)

    def test_el_ultimo_codigo_sigue_valiendo_durante_el_bloqueo(self):
        """
        Bloquear el **envio** no es invalidar lo enviado: quien recibio el
        quinto correo tiene que poder usarlo, o se quedaria una hora fuera
        con un codigo bueno delante.
        """
        self._pedir()
        self.client_record.refresh_from_db()
        self.client_record.code_sends = 5
        self.client_record.code_blocked_until = (
            timezone.now() + timedelta(hours=1)
        )
        self.client_record.save()

        respuesta = self.client.post(self.url, {'code': CODIGO})

        self.assertTrue(respuesta.context['cases'])

    def test_consultar_de_nuevo_durante_el_bloqueo_no_reinicia_nada(self):
        """
        Volver al primer paso y teclear la cedula otra vez es el camino obvio
        para saltarse la espera. No manda correo y devuelve a la pantalla del
        codigo con la hora.
        """
        self._pedir()
        self.client_record.refresh_from_db()
        self.client_record.code_sends = 5
        self.client_record.code_blocked_until = (
            timezone.now() + timedelta(hours=1)
        )
        self.client_record.save()
        mail.outbox.clear()

        respuesta = self._pedir()

        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNotNone(respuesta.context['resend_at'])

    def test_vaciar_la_sesion_no_reinicia_la_escalera(self):
        """
        Si la cuenta viviera en la sesion, tirar la galleta seria el bypass.
        """
        self._pedir()
        self.client.cookies.clear()
        mail.outbox.clear()

        self._pedir()

        self.assertEqual(len(mail.outbox), 0)

    def test_acertar_deja_la_escalera_lista_para_la_proxima(self):
        self._pedir()
        self._adelantar(timedelta(seconds=61))
        self._reenviar()

        self.client.post(self.url, {'code': CODIGO})

        self.client_record.refresh_from_db()
        self.assertEqual(self.client_record.code_sends, 0)


class CodeLifetimeTests(TestCase):
    """Cuanto vive un codigo y cuantas veces se puede fallar."""

    def setUp(self):
        cache.clear()
        self.url = reverse('case_manager:public_query')
        self.client_record = ClientModel.objects.create(
            identification='16484186',
            full_name='Carlos Giraldo',
            email='carlos@example.test',
        )
        CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )
        with patch.object(portal_otp, 'generate_code', return_value=CODIGO):
            self.client.post(self.url, {'identification': '16484186'})

    def test_un_codigo_caducado_no_sirve(self):
        sesion = self.client.session
        datos = sesion[portal_otp.SESSION_KEY]
        datos['expires'] = (
            timezone.now() - timedelta(minutes=1)
        ).isoformat()
        sesion[portal_otp.SESSION_KEY] = datos
        sesion.save()

        respuesta = self.client.post(self.url, {'code': CODIGO})

        self.assertFalse(respuesta.context.get('cases'))

    def test_al_quinto_fallo_el_codigo_se_tira(self):
        """
        Tantear cuesta pedir otro, y pedir otro tiene su escalera. Nadie
        necesita seis intentos para copiar seis cifras de un correo.
        """
        for _ in range(portal_otp.MAX_ATTEMPTS):
            self.client.post(self.url, {'code': '000000'})

        respuesta = self.client.post(self.url, {'code': CODIGO})

        self.assertFalse(respuesta.context.get('cases'))

    def test_el_codigo_no_se_guarda_en_claro(self):
        """
        En la sesion va su HMAC. La sesion va firmada, no cifrada: con el
        motor de galletas firmadas --que es una linea de configuracion de
        distancia-- el codigo viajaria en el navegador.
        """
        guardado = self.client.session[portal_otp.SESSION_KEY]

        self.assertNotIn(CODIGO, str(guardado))
        self.assertEqual(guardado['code_hash'], portal_otp.hash_code(CODIGO))


class MaskedEmailTests(TestCase):
    """El correo tapado, que es lo unico que la pantalla dice del buzon."""

    def _mask(self, correo):
        return ClientModel(
            identification='1', full_name='X', email=correo
        ).masked_email

    def test_tapa_el_centro_y_deja_reconocerlo(self):
        self.assertEqual(
            self._mask('sebasmoralesd@gmail.com'), 'seb****esd@gmail.com'
        )

    def test_el_numero_de_asteriscos_es_fijo(self):
        """
        Uno por letra diria de cuantas letras es el buzon, y eso tampoco hace
        falta para reconocerlo.
        """
        corto = self._mask('abcdefgh@example.com')
        largo = self._mask('abcdefghijklmnopqrst@example.com')

        self.assertEqual(corto.count('*'), largo.count('*'))

    def test_un_buzon_muy_corto_no_se_destapa_entero(self):
        self.assertEqual(self._mask('ana@example.com'), 'a****@example.com')

    def test_sin_correo_no_hay_mascara(self):
        self.assertEqual(self._mask(''), '')


class AccessCodeEmailTests(TestCase):
    """El correo que lleva el codigo."""

    def setUp(self):
        self.client_record = ClientModel.objects.create(
            identification='16484186',
            full_name='Carlos Giraldo',
            email='carlos@example.test',
        )

    def _enviar(self):
        from ..emails import send_access_code

        send_access_code(client=self.client_record, code=CODIGO, minutes=15)
        return mail.outbox[0]

    def test_lleva_el_membrete_dentro_del_mensaje(self):
        """
        Las imagenes remotas las bloquean casi todos los clientes de correo:
        un membrete enlazado saldria como un cuadro roto encima del codigo.
        """
        mensaje = self._enviar()

        self.assertEqual(mensaje.mixed_subtype, 'related')
        self.assertIn(
            '<membrete>',
            [a.get('Content-ID') for a in mensaje.attachments
             if hasattr(a, 'get')],
        )

    def test_no_lleva_la_firma_del_representante_legal(self):
        """
        No hay nada firmado que enviar. Son unos 40 KB por mensaje, y una
        firma escaneada que viaja en cada codigo de acceso acaba circulando.
        """
        cids = [
            a.get('Content-ID') for a in self._enviar().attachments
            if hasattr(a, 'get')
        ]

        self.assertNotIn('<firma>', cids)

    def test_contesta_a_la_direccion_del_despacho(self):
        self.assertEqual(
            self._enviar().reply_to, ['info@propensionesabogados.com']
        )

    def test_el_codigo_sale_en_las_dos_versiones(self):
        """
        Hay quien lee el correo en texto plano, y un correo solo-HTML puntua
        peor en los filtros de spam.
        """
        mensaje = self._enviar()

        self.assertIn(CODIGO, mensaje.body)
        self.assertIn(CODIGO, mensaje.alternatives[0][0])


class OfficeFallbackTests(TestCase):
    """
    El cliente sin correo registrado: su codigo va al despacho.

    Es el caso normal, no el raro: los expedientes que venian del navegador no
    traian correo. Cerrarles el portal los dejaba sin nada que pudieran hacer
    por su cuenta; mandandolo a la oficina, quien llama lo recibe de alguien
    que ya sabe quien es.

    No relaja la acreditacion, **la traslada**: quien entrega el codigo pasa a
    ser el despacho, que conoce al titular, en vez de un buzon que el titular
    controla.
    """

    def setUp(self):
        cache.clear()
        self.url = reverse('case_manager:public_query')
        self.client_record = ClientModel.objects.create(
            identification='13883170',
            full_name='Jose Arcesio Lopez Arias',
            email='',
        )
        CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )

    def _pedir(self):
        with patch.object(portal_otp, 'generate_code', return_value=CODIGO):
            return self.client.post(self.url, {'identification': '13883170'})

    def test_va_a_los_dos_buzones_del_despacho(self):
        self._pedir()

        self.assertEqual(
            sorted(mail.outbox[0].to),
            ['cto@propensionesabogados.com',
             'info@propensionesabogados.com'],
        )

    def test_el_asunto_dice_de_quien_es_el_codigo(self):
        """
        A la oficina le llegarian seis cifras sueltas y no sabria a quien
        darselas. El nombre y la cedula van ya en el asunto para que se vea
        sin abrir el correo.
        """
        self._pedir()

        self.assertIn('Jose Arcesio Lopez Arias', mail.outbox[0].subject)
        self.assertIn('13883170', mail.outbox[0].subject)

    def test_el_cuerpo_lleva_al_cliente_y_pide_registrar_su_correo(self):
        """
        Sin el recordatorio, este mismo correo vuelve a llegar la proxima vez
        que el cliente consulte, y la siguiente.
        """
        self._pedir()
        html = mail.outbox[0].alternatives[0][0]

        self.assertIn('Jose Arcesio Lopez Arias', html)
        self.assertIn('13883170', html)
        self.assertIn('register their email address', html)
        self.assertIn(CODIGO, html)

    def test_no_le_dice_al_despacho_que_nadie_le_pide_el_codigo(self):
        """
        El aviso de «nadie de Propensiones te pedira este codigo» es para el
        titular. Mandarselo a la propia oficina, que es quien lo va a dictar
        por telefono, es decir lo contrario de lo que toca hacer.
        """
        self._pedir()

        self.assertNotIn(
            'will ever ask you for this code',
            mail.outbox[0].alternatives[0][0],
        )

    def test_el_codigo_sirve_igual(self):
        """
        Lo que cambia es a donde va, no lo que hace: quien lo teclea entra.
        """
        self._pedir()

        respuesta = self.client.post(self.url, {'code': CODIGO})

        self.assertTrue(respuesta.context['cases'])

    def test_la_escalera_tambien_frena_los_que_van_al_despacho(self):
        """
        Si no, hostigar una cedula sin correo llenaria el buzon de la propia
        oficina, que es donde menos conviene.
        """
        self._pedir()
        mail.outbox.clear()

        self._pedir()

        self.assertEqual(len(mail.outbox), 0)

    def test_en_cuanto_tiene_correo_deja_de_ir_al_despacho(self):
        self.client_record.email = 'jose@example.test'
        self.client_record.save(update_fields=['email'])

        respuesta = self._pedir()

        self.assertEqual(mail.outbox[0].to, ['jose@example.test'])
        self.assertFalse(respuesta.context['sent_to_office'])

    @override_settings(CASE_MANAGER_OFFICE_RECIPIENTS=[])
    def test_sin_buzon_de_oficina_configurado_se_dice(self):
        """
        Quedarse callado dejaria al cliente esperando un codigo que no existe.
        """
        respuesta = self._pedir()

        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(respuesta.context['show_contact'])

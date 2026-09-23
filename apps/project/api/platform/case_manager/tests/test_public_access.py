"""
La puerta del portal publico de consulta.

Lo que se prueba aqui es, literalmente, lo que antes decidia el navegador del
visitante con el expediente de todo el despacho ya descargado. Cada una de
estas pruebas falla si esa decision vuelve al cliente.
"""

from unittest.mock import patch

from apps.common.utils.models import IPBlockedModel
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .. import attempts, portal_otp
from ..choices import Mandate, Procedure, Service, Stage
from ..models import CaseFinanceModel, CaseModel, ClientModel

CODIGO = '123456'


def pedir_codigo(test_client, identification='16484186', code=CODIGO):
    """El primer paso: la cedula. Devuelve la respuesta."""
    with patch.object(portal_otp, 'generate_code', return_value=code):
        return test_client.post(
            reverse('case_manager:public_query'),
            {'identification': identification},
        )


def identificarse(test_client, identification='16484186', code=CODIGO):
    """
    Los dos pasos del portal en una linea: la cedula y el codigo del correo.

    El codigo se fija en vez de leerlo del buzon porque lo que prueban casi
    todas las clases de abajo es lo que pasa **despues** de entrar. Las que
    prueban el codigo en si miran `mail.outbox`.
    """
    pedir_codigo(test_client, identification, code)
    return test_client.post(
        reverse('case_manager:public_query'), {'code': code}
    )


# Sin el middleware de bloqueo por medio: lo que se prueba aqui es la vista,
# y el middleware tiene su propia prueba mas abajo.
SIN_MIDDLEWARE_DE_BLOQUEO = [
    middleware
    for middleware in settings.MIDDLEWARE
    if 'DetectSuspiciousRequest' not in middleware
]


class PublicQueryTests(TestCase):
    """Identificacion y clave contra el servidor."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('case_manager:public_query')

        cls.client_record = ClientModel.objects.create(
            identification='16484186',
            full_name='Carlos Emiro Giraldo Lozada',
            email='cliente16484186@example.test'
        )
        cls.case = CaseModel.objects.create(
            client=cls.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )
        CaseFinanceModel.objects.create(
            case=cls.case,
            mandate=Mandate.PAYMENT,
            agreed_fee=4_000_000,
            paid_amount=1_000_000,
        )

        cls.inactive = ClientModel.objects.create(
            identification='99999999',
            full_name='Rosa Inactiva',
            is_active=False,
            email='cliente99999999@example.test'
        )
        CaseModel.objects.create(
            client=cls.inactive,
            service=Service.JUDICIAL,
            stage=Stage.UNDER_REVIEW,
        )

    def setUp(self):
        cache.clear()

    # --- los dos pasos ---------------------------------------------------
    def test_la_cedula_sola_no_abre_nada(self):
        """
        El primer paso no ensena expediente: manda un codigo y espera.

        Es el cambio entero. Antes la cedula iba acompanada de una «clave» que
        se calculaba **con la cedula delante** --la inicial del nombre mas sus
        cuatro ultimos digitos--, asi que el unico dato necesario para abrir
        un expediente ajeno era un dato que circula.
        """
        response = pedir_codigo(self.client)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get('cases'))
        self.assertNotContains(response, 'Carlos Emiro Giraldo Lozada')

    def test_el_codigo_sale_al_correo_registrado(self):
        pedir_codigo(self.client)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['cliente16484186@example.test'])
        self.assertIn(CODIGO, mail.outbox[0].body)

    def test_la_pantalla_dice_a_donde_fue_el_codigo_sin_ensenar_el_correo(self):
        """
        Tapado por el centro: el cliente tiene que poder reconocer su buzon
        --si no, no sabe a cual mirar ni si el que consta es el suyo-- sin que
        la pantalla sirva para leer el correo de un tercero.
        """
        response = pedir_codigo(self.client)

        self.assertContains(response, 'cli****186@example.test')
        self.assertNotContains(response, 'cliente16484186@example.test')

    def test_el_codigo_correcto_abre_el_expediente(self):
        response = identificarse(self.client)

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.case, response.context['cases'])

    def test_el_codigo_equivocado_no_abre_nada(self):
        pedir_codigo(self.client)
        response = self.client.post(self.url, {'code': '000000'})

        self.assertFalse(response.context.get('cases'))
        self.assertTrue(response.context.get('code_error'))

    def test_un_codigo_no_sirve_dos_veces(self):
        """
        Se quema al usarlo: quien vea el correo por encima del hombro --o lo
        recupere de un buzon compartido-- no entra cuando quiera.
        """
        identificarse(self.client)
        self.client.session.flush()

        response = self.client.post(self.url, {'code': CODIGO})

        self.assertFalse(response.context.get('cases'))

    def test_el_codigo_de_un_cliente_no_abre_el_de_otro(self):
        """
        La sesion recuerda **de quien** es el codigo. Sin eso, pedirlo para la
        cedula propia y teclearlo mientras se dice ser otro seria la puerta.
        """
        otro = ClientModel.objects.create(
            identification='55555555', full_name='Otro Titular',
            email='cliente55555555@example.test',
        )
        CaseModel.objects.create(
            client=otro, service=Service.JUDICIAL, stage=Stage.IN_PROGRESS
        )

        pedir_codigo(self.client, '16484186')
        response = self.client.post(self.url, {'code': CODIGO})

        self.assertNotContains(response, 'Otro Titular')
        self.assertIn(self.case, response.context['cases'])

    def test_la_cedula_con_puntos_es_la_misma_cedula(self):
        response = identificarse(self.client, '16.484.186')

        self.assertIn(self.case, response.context['cases'])

    def test_a_un_cliente_sin_correo_el_codigo_le_llega_al_despacho(self):
        """
        No se queda fuera. Antes se le cerraba el portal sin que hubiera nada
        que pudiera hacer por su cuenta, y los expedientes importados vienen
        casi todos sin correo.
        """
        ClientModel.objects.create(
            identification='44444444', full_name='Sin Correo', email='',
        )

        response = pedir_codigo(self.client, '44444444')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            sorted(mail.outbox[0].to),
            ['cto@propensionesabogados.com',
             'info@propensionesabogados.com'],
        )
        self.assertTrue(response.context['sent_to_office'])

    def test_la_pantalla_le_dice_que_lo_tiene_la_oficina_y_a_donde_llamar(self):
        ClientModel.objects.create(
            identification='44444444', full_name='Sin Correo', email='',
        )

        response = pedir_codigo(self.client, '44444444')

        self.assertContains(response, 'sent the access code to our offices')
        self.assertContains(response, '+57 301 228 3818')
        # El campo sigue ahi: el codigo existe y se lo dictan por telefono.
        self.assertContains(response, 'name="code"')

    def test_si_el_correo_no_sale_se_dice(self):
        """
        Prometer un codigo que no va a llegar deja a alguien mirando un campo
        vacio sin saber cuanto esperar.
        """
        with patch.object(
            portal_otp, 'send_access_code', create=True, side_effect=OSError
        ), patch(
            'apps.project.api.platform.case_manager.emails.send_access_code',
            side_effect=OSError,
        ):
            response = pedir_codigo(self.client)

        self.assertTrue(response.context['show_contact'])
        self.assertFalse(response.context.get('masked_email'))

    # --- lo que no se puede averiguar ------------------------------------
    def test_una_cedula_que_no_existe_lo_dice(self):
        """
        Con el codigo al correo, decir «no hay nada con ese numero» ya no
        entrega una credencial a nadie: quien no es cliente se entera de que
        no lo es, y quien se equivoco de digito lo corrige en vez de quedarse
        esperando un correo que no existe.
        """
        response = self.client.post(self.url, {'identification': '11111111'})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.context.get('masked_email'))
        self.assertEqual(len(mail.outbox), 0)

    def test_un_cliente_sin_vigencia_recibe_su_codigo_igual(self):
        """
        Si se le dijera «no encontramos nada» se pondria a probar cedulas
        creyendo que se equivoco de numero. Se le manda el codigo, entra, y la
        pantalla le dice que su proceso esta inactivo y a donde llamar.
        """
        response = identificarse(self.client, '99999999')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['inactive'])
        self.assertFalse(response.context.get('cases'))
        self.assertContains(response, '+57 301 228 3818')

    def test_la_pantalla_de_inactivo_no_ensena_ni_un_dato_del_expediente(self):
        """
        Decirle que llame no es abrirle el expediente: sigue sin vigencia.
        """
        response = identificarse(self.client, '99999999')

        self.assertNotContains(response, 'Rosa Inactiva')
        self.assertFalse(response.context.get('client'))

    # --- lo que viaja al navegador ---------------------------------------
    def test_la_pagina_vacia_no_trae_ningun_expediente(self):
        """
        Un `GET` no puede traer datos de nadie.

        Esta es la prueba que sostiene el cambio entero: antes, este mismo
        `GET` traia el despacho completo dentro del HTML.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get('cases'))
        self.assertNotContains(response, 'Carlos Emiro Giraldo Lozada')
        self.assertNotContains(response, '16484186')

    def test_entrar_no_trae_los_expedientes_de_los_demas(self):
        otro = ClientModel.objects.create(
            identification='77777777', full_name='Otro Cliente',
            email='cliente77777777@example.test'
        )
        CaseModel.objects.create(
            client=otro, service=Service.CONCILIATION, stage=Stage.FINAL_STAGE
        )

        response = identificarse(self.client)

        self.assertNotContains(response, 'Otro Cliente')
        self.assertNotContains(response, '77777777')

    def test_el_dinero_no_sale_al_portal(self):
        """
        El expediente es del cliente; lo que se le cobra es de puertas
        adentro. Van en modelos distintos justamente para que no se escape.
        """
        response = identificarse(self.client)

        self.assertNotContains(response, '4000000')
        self.assertNotContains(response, '3000000')


@override_settings(CASE_MANAGER_MAX_ATTEMPTS=3, MIDDLEWARE=SIN_MIDDLEWARE_DE_BLOQUEO)
class AttemptLimitTests(TestCase):
    """
    El limite de intentos por IP.

    Es lo que frena a quien recorre cedulas para saber quien es cliente del
    despacho, y a quien tantea codigos de seis cifras. La escalera de
    reenvios (`portal_otp`) protege otra cosa --el buzon del cliente-- y
    tiene sus propias pruebas mas abajo.
    """

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('case_manager:public_query')
        ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test'
        )

    def setUp(self):
        cache.clear()

    def _fallar(self, veces):
        """Cedulas que no son de nadie, que es el tanteo que esto frena."""
        for numero in range(veces):
            self.client.post(
                self.url, {'identification': f'8888888{numero}'}
            )

    def test_al_llegar_al_tope_se_bloquea_la_ip(self):
        self._fallar(3)

        self.assertTrue(
            IPBlockedModel.objects.filter(
                reason=IPBlockedModel.ReasonsChoices.CASE_QUERY_ATTEMPTS
            ).exists()
        )

    def test_el_bloqueo_lleva_siempre_fecha_de_fin(self):
        """
        Un bloqueo sin `blocked_until` no bloquea a nadie: el middleware
        filtra por `blocked_until__gte=now` y una fila con ese campo a NULL
        no cumple esa condicion en SQL.
        """
        self._fallar(3)

        bloqueo = IPBlockedModel.objects.latest('created')
        self.assertIsNotNone(bloqueo.blocked_until)

    def test_antes_del_tope_no_hay_bloqueo(self):
        self._fallar(2)

        self.assertFalse(IPBlockedModel.objects.exists())

    def test_un_codigo_equivocado_tambien_cuenta(self):
        """
        Si no, tantear seis cifras saldria gratis mientras que equivocarse de
        cedula no, y el tanteo se iria por donde no cuesta.
        """
        pedir_codigo(self.client)
        self.client.post(self.url, {'code': '000000'})

        self.assertEqual(attempts.attempts_for('127.0.0.1'), 1)

    def test_acertar_borra_la_cuenta(self):
        """Dos despistes y un acierto no dejan a nadie a un fallo del cierre."""
        self._fallar(2)

        identificarse(self.client)

        self.assertEqual(attempts.attempts_for('127.0.0.1'), 0)

    def test_una_ip_bloqueada_recibe_429(self):
        self._fallar(3)

        response = self.client.post(
            self.url, {'identification': '16484186'}
        )

        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.context.get('cases'))


class ForwardedHeaderTests(TestCase):
    """
    De donde se saca la IP.

    Si se confiara en `X-Forwarded-For` sin un proxy delante, quien llama
    elegiria su propia identidad y cambiarla en cada intento dejaria el
    contador a cero para siempre.
    """

    def _peticion(self, **extra):
        from django.test import RequestFactory

        return RequestFactory().post('/', **extra)

    def test_por_defecto_se_ignora_la_cabecera(self):
        peticion = self._peticion(
            HTTP_X_FORWARDED_FOR='1.2.3.4', REMOTE_ADDR='10.0.0.1'
        )

        self.assertEqual(attempts.client_ip(peticion), '10.0.0.1')

    @override_settings(USE_X_FORWARDED_FOR=True)
    def test_solo_se_mira_si_el_despliegue_lo_declara(self):
        peticion = self._peticion(
            HTTP_X_FORWARDED_FOR='1.2.3.4, 10.0.0.9', REMOTE_ADDR='10.0.0.1'
        )

        self.assertEqual(attempts.client_ip(peticion), '1.2.3.4')


class VariosAsuntosTests(TestCase):
    """
    Un cliente con mas de un asunto los ve **todos**.

    Antes la vista hacia `.first()` y ensenaba uno solo. El modelo siempre fue
    uno a muchos --un cliente puede llevar a la vez una pension y una
    conciliacion--, asi que quien preguntaba por uno veia el otro y no
    entendia por que.
    """

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('case_manager:public_query')
        cls.client_record = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test'
        )
        cls.pension = CaseModel.objects.create(
            client=cls.client_record,
            service=Service.JUDICIAL,
            subtype='Pensión de invalidez',
            stage=Stage.IN_PROGRESS,
        )
        cls.conciliacion = CaseModel.objects.create(
            client=cls.client_record,
            service=Service.CONCILIATION,
            subtype='Alimentos',
            stage=Stage.FINAL_STAGE,
        )

    def setUp(self):
        cache.clear()

    def _consultar(self):
        return identificarse(self.client)

    def test_salen_los_dos(self):
        response = self._consultar()

        devueltos = list(response.context['cases'])
        self.assertIn(self.pension, devueltos)
        self.assertIn(self.conciliacion, devueltos)

    def test_cada_uno_con_su_etapa(self):
        """
        Lo que hace util verlos juntos: van por sitios distintos.
        """
        response = self._consultar()

        self.assertContains(response, 'Pensión de invalidez')
        self.assertContains(response, 'Alimentos')
        self.assertContains(response, 'En trámite')
        self.assertContains(response, 'Etapa final')

    def test_un_asunto_sin_vigencia_no_sale(self):
        CaseModel.objects.filter(
            pk=self.conciliacion.pk).update(is_active=False)

        devueltos = list(self._consultar().context['cases'])

        self.assertEqual(devueltos, [self.pension])

    def test_solo_el_autorizado_ensena_su_paz_y_salvo(self):
        """
        El permiso es **por asunto**, no por cliente: se puede estar a paz y
        salvo de una cosa y deber otra.
        """
        CaseModel.objects.filter(pk=self.pension.pk).update(
            paz_y_salvo_authorized=True
        )

        response = self._consultar()

        self.assertContains(
            response, reverse('case_manager:paz_y_salvo',
                              args=[self.pension.pk])
        )
        self.assertNotContains(
            response,
            reverse('case_manager:paz_y_salvo', args=[self.conciliacion.pk]),
        )

    def test_siguen_sin_salir_los_de_otros_clientes(self):
        otro = ClientModel.objects.create(
            identification='77777777', full_name='Otra Persona',
            email='cliente77777777@example.test'
        )
        CaseModel.objects.create(
            client=otro, service=Service.JUDICIAL, stage=Stage.UNDER_REVIEW
        )

        response = self._consultar()

        self.assertNotContains(response, 'Otra Persona')
        self.assertNotContains(response, '77777777')


class PublicCardFieldsTests(TestCase):
    """
    Los datos de la tarjeta, que son los del diseno aprobado.

    La etapa y el radicado estaban en el bloque de detalle de abajo, entre el
    despacho y la ciudad; quien entraba a mirar «por donde va lo mio» tenia
    que bajar a buscarlos. El diseno los sube arriba y anade la modalidad del
    contrato, que hasta ahora no salia en ninguna parte del portal.
    """

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('case_manager:public_query')
        cls.client_record = ClientModel.objects.create(
            identification='16484186',
            full_name='Carlos Emiro Giraldo Lozada',
            email='cliente16484186@example.test'
        )

    def consultar(self):
        return identificarse(self.client)

    def test_la_instancia_sale_venga_del_bloque_que_venga(self):
        """
        El asunto judicial la guarda en `instance` y la querella policiva en
        `police_instance`. El cliente no tiene por que saber cual le toco.
        """
        judicial = CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            procedure=Procedure.ORDINARY,
            stage=Stage.IN_PROGRESS,
            instance='Primera instancia',
        )
        policiva = CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            procedure=Procedure.POLICE,
            stage=Stage.IN_PROGRESS,
            police_instance='Segunda instancia',
        )

        self.assertEqual(judicial.public_instance, 'Primera instancia')
        self.assertEqual(policiva.public_instance, 'Segunda instancia')

        respuesta = self.consultar()

        self.assertContains(respuesta, 'Primera instancia')
        self.assertContains(respuesta, 'Segunda instancia')

    def test_la_cuota_litis_sale_con_su_porcentaje(self):
        """
        «Cuota litis» a secas no le dice a nadie cuanto va a pagar.
        """
        caso = CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )
        CaseFinanceModel.objects.create(
            case=caso,
            mandate=Mandate.CONTINGENCY,
            contingency_percentage=30,
            contingency_value=5_000_000,
        )

        self.assertEqual(caso.public_mandate, 'Cuota litis (30 %)')
        self.assertContains(self.consultar(), 'Cuota litis (30 %)')

    def test_un_asunto_sin_bloque_economico_no_revienta(self):
        """
        El bloque se rellena despues de dar de alta el asunto, y entre una
        cosa y otra el cliente ya puede estar consultando.
        """
        caso = CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )

        self.assertEqual(caso.public_mandate, '—')
        self.assertEqual(self.consultar().status_code, 200)

    def test_el_dinero_no_se_asoma_al_portal(self):
        """
        La modalidad si sale --esta en el diseno aprobado-- pero las cifras
        no: ni lo pactado, ni lo pagado, ni lo que se debe.
        """
        caso = CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            stage=Stage.IN_PROGRESS,
        )
        CaseFinanceModel.objects.create(
            case=caso,
            mandate=Mandate.PAYMENT,
            agreed_fee=8_123_456,
            paid_amount=3_111_222,
        )

        respuesta = self.consultar()

        self.assertContains(respuesta, 'Modalidad de pago')
        self.assertNotContains(respuesta, '8123456')
        self.assertNotContains(respuesta, '8.123.456')
        self.assertNotContains(respuesta, '3111222')

    def test_la_tarjeta_no_repite_la_instancia_en_el_detalle(self):
        """
        Subirla arriba sin quitarla de abajo la habria dejado dos veces en la
        misma tarjeta.
        """
        caso = CaseModel.objects.create(
            client=self.client_record,
            service=Service.JUDICIAL,
            procedure=Procedure.ORDINARY,
            stage=Stage.IN_PROGRESS,
            instance='Primera instancia',
            case_number='2026-00123-00',
            court='Juzgado del Circuito',
        )
        etiquetas = [etiqueta for etiqueta, _valor in caso.detail_rows]

        self.assertNotIn('CURRENT INSTANCE', etiquetas)
        self.assertNotIn('CASE NUMBER', etiquetas)
        self.assertIn('COURT', etiquetas)

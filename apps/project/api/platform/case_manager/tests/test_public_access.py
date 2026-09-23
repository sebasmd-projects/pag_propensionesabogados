"""
La puerta del portal publico de consulta.

Lo que se prueba aqui es, literalmente, lo que antes decidia el navegador del
visitante con el expediente de todo el despacho ya descargado. Cada una de
estas pruebas falla si esa decision vuelve al cliente.
"""

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.common.utils.models import IPBlockedModel

from .. import attempts
from ..choices import Mandate, Procedure, Service, Stage
from ..models import CaseFinanceModel, CaseModel, ClientModel

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
        )
        CaseModel.objects.create(
            client=cls.inactive,
            service=Service.JUDICIAL,
            stage=Stage.UNDER_REVIEW,
        )

    def setUp(self):
        cache.clear()

    # --- la clave --------------------------------------------------------
    def test_la_clave_es_la_inicial_mas_los_cuatro_ultimos_digitos(self):
        """La regla aprobada, ahora calculada en el servidor."""
        self.assertEqual(self.client_record.access_key, 'C4186')

    def test_con_la_clave_correcta_se_ve_el_expediente(self):
        response = self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'C4186'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.case, response.context['cases'])

    def test_la_cedula_con_puntos_es_la_misma_cedula(self):
        response = self.client.post(
            self.url,
            {'identification': '16.484.186', 'access_key': 'C4186'},
        )

        self.assertIn(self.case, response.context['cases'])

    def test_con_la_clave_equivocada_no_se_ve_nada(self):
        response = self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'X9999'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.context.get('cases'))

    def test_la_clave_distingue_mayusculas(self):
        """`c4186` no es `C4186`: la inicial va en mayuscula."""
        response = self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'c4186'},
        )

        self.assertFalse(response.context.get('cases'))

    # --- lo que no se puede averiguar ------------------------------------
    def test_una_cedula_que_no_existe_responde_lo_mismo_que_una_clave_mala(self):
        """
        El formulario no puede servir para saber quien es cliente.

        Con mensajes distintos, probar cedulas convierte el portal en un
        listado del despacho: "clave incorrecta" confirma la persona.
        """
        desconocida = self.client.post(
            self.url,
            {'identification': '11111111', 'access_key': 'A1111'},
        )
        clave_mala = self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'Z0000'},
        )

        self.assertEqual(desconocida.status_code, clave_mala.status_code)
        self.assertEqual(
            desconocida.context['error'], clave_mala.context['error']
        )

    def test_un_cliente_sin_vigencia_ve_la_pantalla_de_proceso_inactivo(self):
        """
        Su clave era **correcta**, asi que no se le contesta «credenciales
        invalidas».

        Antes si, y el resultado era el contrario del que se buscaba: quien
        tenia su proceso cerrado no entendia el mensaje, daba por hecho que se
        habia equivocado de clave, y se ponia a probar claves correctas una
        detras de otra hasta agotar los intentos de su propia IP. No se le
        oculta nada que no haya demostrado ya al acertar: se le dice que su
        proceso esta inactivo y a donde llamar, que es lo unico que puede
        hacer.
        """
        response = self.client.post(
            self.url,
            {'identification': '99999999', 'access_key': 'R9999'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['inactive'])
        self.assertFalse(response.context.get('cases'))
        self.assertContains(response, '+57 301 228 3818')

    def test_la_pantalla_de_inactivo_no_ensena_ni_un_dato_del_expediente(self):
        """
        Decirle que llame no es abrirle el expediente: sigue sin vigencia.
        """
        response = self.client.post(
            self.url,
            {'identification': '99999999', 'access_key': 'R9999'},
        )

        self.assertNotContains(response, '99999999')
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

    def test_entrar_con_una_clave_no_trae_los_expedientes_de_los_demas(self):
        otro = ClientModel.objects.create(
            identification='77777777', full_name='Otro Cliente'
        )
        CaseModel.objects.create(
            client=otro, service=Service.CONCILIATION, stage=Stage.FINAL_STAGE
        )

        response = self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'C4186'},
        )

        self.assertNotContains(response, 'Otro Cliente')
        self.assertNotContains(response, '77777777')

    def test_el_dinero_no_sale_al_portal(self):
        """
        El expediente es del cliente; lo que se le cobra es de puertas
        adentro. Van en modelos distintos justamente para que no se escape.
        """
        response = self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'C4186'},
        )

        self.assertNotContains(response, '4000000')
        self.assertNotContains(response, '3000000')


@override_settings(CASE_MANAGER_MAX_ATTEMPTS=3, MIDDLEWARE=SIN_MIDDLEWARE_DE_BLOQUEO)
class AttemptLimitTests(TestCase):
    """
    El limite de intentos.

    Mientras la clave sea la inicial mas cuatro digitos, esto es lo unico
    que la separa de diez mil intentos automatizados.
    """

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('case_manager:public_query')
        ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo'
        )

    def setUp(self):
        cache.clear()

    def _fallar(self, veces):
        for _ in range(veces):
            self.client.post(
                self.url,
                {'identification': '16484186', 'access_key': 'X0000'},
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

    def test_acertar_borra_la_cuenta(self):
        """Dos despistes y un acierto no dejan a nadie a un fallo del cierre."""
        self._fallar(2)

        self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'C4186'},
        )

        self.assertEqual(attempts.attempts_for('127.0.0.1'), 0)

    def test_una_ip_bloqueada_recibe_429(self):
        self._fallar(3)

        response = self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'C4186'},
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
            identification='16484186', full_name='Carlos Giraldo'
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
        return self.client.post(
            self.url, {'identification': '16484186', 'access_key': 'C4186'}
        )

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
        CaseModel.objects.filter(pk=self.conciliacion.pk).update(is_active=False)

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
            response, reverse('case_manager:paz_y_salvo', args=[self.pension.pk])
        )
        self.assertNotContains(
            response,
            reverse('case_manager:paz_y_salvo', args=[self.conciliacion.pk]),
        )

    def test_siguen_sin_salir_los_de_otros_clientes(self):
        otro = ClientModel.objects.create(
            identification='77777777', full_name='Otra Persona'
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
        )

    def consultar(self):
        return self.client.post(
            self.url,
            {'identification': '16484186', 'access_key': 'C4186'},
        )

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

"""
Paz y salvo en linea: autorizar, retirar y reintentar certifican en el propio
request, sin hilos y sin el comando `certify_pending_paz_y_salvo`.

`TransactionTestCase` y no `TestCase`: el `on_commit` tiene que correr de
verdad al salir de la transaccion de la vista, como en produccion. gea esta
sustituido por `FakeGea` (ver `test_paz_y_salvo_certified`).
"""

import shutil
import tempfile
from unittest import mock

from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from ..choices import Service, Stage
from ..models import CaseModel, ClientModel, PazYSalvoDocumentModel
from .test_access import login_as, make_user
from .test_paz_y_salvo_certified import BASE, KEY, PUBLIC, FakeGea
from .test_public_access import identificarse

Status = PazYSalvoDocumentModel.Status
ES = {'HTTP_ACCEPT_LANGUAGE': 'es'}


def textos(respuesta):
    return [str(m) for m in respuesta.wsgi_request._messages]


@override_settings(
    GEA_CERT_API_BASE=BASE, GEA_ISSUER_SLUG='propensiones',
    SERVER_KEY=KEY, PAZ_Y_SALVO_PUBLIC_BASE=PUBLIC,
    PAZ_Y_SALVO_MAX_ATTEMPTS=3,
)
class InlineBase(TransactionTestCase):
    def setUp(self):
        self.private = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.private, True)
        patcher = override_settings(PRIVATE_MEDIA_ROOT=self.private)
        patcher.enable()
        self.addCleanup(patcher.disable)

        self.gea = FakeGea()
        for target, replacement in (
            ('apps.project.case_manager.gea_client.'
             'requests.request', self.gea),
            # En linea no hay hilos: si se lanzara uno, la prueba revienta.
            ('apps.project.case_manager.paz_y_salvo.'
             'threading.Thread', mock.Mock(side_effect=AssertionError(
                 'no debe lanzarse un hilo'))),
        ):
            p = mock.patch(target, replacement)
            p.start()
            self.addCleanup(p.stop)

        cliente = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test')
        self.case = CaseModel.objects.create(
            client=cliente, service=Service.JUDICIAL, stage=Stage.FINISHED,
            subtype='Pensión de invalidez', case_number='2024-00123-00')
        make_user('abogada', gestor=True)
        self.gestor = Client()
        login_as(self.gestor, 'abogada')
        self.toggle_url = reverse(
            'case_manager:gestor_case_toggle_settlement', args=[self.case.pk])
        self.retry_url = reverse(
            'case_manager:gestor_case_retry_certification',
            args=[self.case.pk])

    def nuevo_navegador(self):
        """Sesion limpia: los mensajes de pasos previos no estorban."""
        self.gestor = Client()
        login_as(self.gestor, 'abogada')

    def vigente(self):
        return PazYSalvoDocumentModel.objects.filter(
            case=self.case).exclude(status=Status.REVOKED).get()


class ToggleInlineTests(InlineBase):
    def test_autorizar_en_la_tabla_certifica_sin_comando(self):
        respuesta = self.gestor.post(self.toggle_url, **ES)

        self.assertEqual(respuesta.status_code, 302)
        doc = self.vigente()
        self.assertEqual(doc.status, Status.CERTIFIED)
        self.assertTrue(doc.public_copy_file.name)
        self.assertEqual(len(self.gea.issue_calls()), 1)
        self.assertIn(
            'Paz y salvo habilitado y certificado para Carlos Giraldo.',
            textos(respuesta))

    def test_retirar_revoca_en_gea_en_linea(self):
        self.gestor.post(self.toggle_url, **ES)
        gea_id = self.vigente().gea_document_id
        self.nuevo_navegador()

        respuesta = self.gestor.post(self.toggle_url, **ES)

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.gea.revoked, [gea_id])
        doc = PazYSalvoDocumentModel.objects.get(case=self.case)
        self.assertEqual(doc.status, Status.REVOKED)
        self.assertTrue(doc.gea_revoked)
        self.assertIn('Paz y salvo retirado a Carlos Giraldo.',
                      textos(respuesta))

    def test_gea_caido_no_rompe_el_request_y_avisa(self):
        self.gea.mode = 'down'

        respuesta = self.gestor.post(self.toggle_url, **ES)

        self.assertEqual(respuesta.status_code, 302)
        self.case.refresh_from_db()
        self.assertTrue(self.case.paz_y_salvo_authorized)
        doc = self.vigente()
        self.assertEqual(doc.status, Status.FAILED)
        self.assertTrue(doc.last_error)
        mensajes = textos(respuesta)
        self.assertEqual(len(mensajes), 1)
        self.assertIn('aún no está certificado', mensajes[0])
        self.assertIn(doc.last_error, mensajes[0])
        self.assertNotIn(KEY, mensajes[0])

    def test_una_excepcion_inesperada_no_rompe_el_request(self):
        with mock.patch(
                'apps.project.case_manager.paz_y_salvo.certify',
                side_effect=RuntimeError('boom')):
            respuesta = self.gestor.post(self.toggle_url, **ES)

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.vigente().status, Status.PENDING)

    def test_retirar_con_gea_caido_avisa_de_la_revocacion_pendiente(self):
        self.gestor.post(self.toggle_url, **ES)
        self.gea.mode = 'revoke_down'
        self.nuevo_navegador()

        respuesta = self.gestor.post(self.toggle_url, **ES)

        self.assertEqual(respuesta.status_code, 302)
        doc = PazYSalvoDocumentModel.objects.get(case=self.case)
        self.assertEqual(doc.status, Status.REVOKED)
        self.assertFalse(doc.gea_revoked)
        self.assertIn('revocación en gea está pendiente',
                      textos(respuesta)[0])

    @override_settings(PAZ_Y_SALVO_CERTIFY_ASYNC=True)
    def test_en_modo_asincrono_se_lanza_un_hilo(self):
        hilo = mock.Mock()
        with mock.patch(
                'apps.project.case_manager.paz_y_salvo.'
                'threading.Thread', hilo):
            self.gestor.post(self.toggle_url)

        hilo.assert_called_once()
        self.assertEqual(self.vigente().status, Status.PENDING)


class RetryInlineTests(InlineBase):
    def test_reintentar_certifica_en_linea_y_dice_que_salio_bien(self):
        self.gea.mode = 'down'
        self.gestor.post(self.toggle_url)
        self.assertEqual(self.vigente().status, Status.FAILED)
        self.gea.mode = 'ok'
        self.nuevo_navegador()

        respuesta = self.gestor.post(self.retry_url, **ES)

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta['Location'], reverse(
            'case_manager:gestor_case_update', args=[self.case.pk]))
        self.assertEqual(self.vigente().status, Status.CERTIFIED)
        self.assertEqual(textos(respuesta), ['El paz y salvo quedó certificado.'])

    def test_reintentar_con_fallo_muestra_el_motivo(self):
        self.gea.mode = 'down'
        self.gestor.post(self.toggle_url)
        self.nuevo_navegador()

        respuesta = self.gestor.post(self.retry_url, **ES)

        self.assertEqual(respuesta.status_code, 302)
        doc = self.vigente()
        self.assertEqual(doc.status, Status.FAILED)
        mensajes = textos(respuesta)
        self.assertEqual(len(mensajes), 1)
        self.assertTrue(mensajes[0].startswith('La certificación falló: '))
        self.assertIn(doc.last_error, mensajes[0])

    def test_reintentar_sin_nada_que_reintentar(self):
        self.gestor.post(self.toggle_url)    # queda CERTIFIED
        self.nuevo_navegador()

        respuesta = self.gestor.post(self.retry_url, **ES)

        self.assertEqual(textos(respuesta), ['No hay nada que reintentar.'])
        self.assertEqual(len(self.gea.issue_calls()), 1)

    def test_la_ficha_tras_reintentar_ensena_el_estado_y_el_mensaje(self):
        self.gea.mode = 'down'
        self.gestor.post(self.toggle_url)
        self.gea.mode = 'ok'
        self.nuevo_navegador()

        respuesta = self.gestor.post(self.retry_url, follow=True, **ES)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'El paz y salvo quedó certificado.')
        self.assertContains(respuesta, 'Certificado')
        self.assertContains(respuesta, 'Descargar copia distribuible')


class ClientViewButtonTests(InlineBase):
    def test_el_boton_va_despues_de_la_hoja_y_en_espanol(self):
        self.gestor.post(self.toggle_url)
        navegador = Client()
        identificarse(navegador, '16484186')

        respuesta = navegador.get(
            reverse('case_manager:paz_y_salvo', args=[self.case.pk]))

        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()
        self.assertIn('Descargar copia distribuible', html)
        self.assertNotIn('Download distributable copy', html)
        self.assertGreater(html.index('accionesPS'), html.index('paginaPS'))
        self.assertGreater(
            html.index('accionesPS'), html.index('Constancia electr'))
        self.assertIn('noPrint accionesPS', html)

    def test_documento_sin_certificar_avisa_en_espanol_tras_la_hoja(self):
        self.gea.mode = 'down'
        self.gestor.post(self.toggle_url)
        navegador = Client()
        identificarse(navegador, '16484186')

        html = navegador.get(
            reverse('case_manager:paz_y_salvo', args=[self.case.pk])
        ).content.decode()

        self.assertIn('La copia certificada se está preparando', html)
        self.assertGreater(html.index('avisoPS'), html.index('paginaPS'))

"""
El paz y salvo certificado por gea.

gea nunca se llama de verdad: `requests.request` esta sustituido por `FakeGea`,
que hace lo que documenta `external.py` de gea (idempotencia por
`idempotency_key`, 201 la primera vez y 200 despues, copia distribuible por
GET, revocacion por POST) y deja anotado cada intercambio. Los hilos se
ejecutan en linea: `threading.Thread` esta sustituido por una clase que corre
el objetivo al llamar a `start()`.
"""

import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone as dt_timezone
from io import StringIO
from unittest import mock

import requests
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from .. import paz_y_salvo, paz_y_salvo_pdf
from ..choices import Service, Stage
from ..models import CaseModel, ClientModel, PazYSalvoDocumentModel
from .test_access import login_as, make_user
from .test_public_access import identificarse

Status = PazYSalvoDocumentModel.Status
KEY = 'test-issuer-key-' + 'x' * 32
BASE = 'https://gea.test'
PUBLIC = 'https://propensionesabogados.com'


class FakeResponse:
    def __init__(self, status_code, body=None, content=None):
        self.status_code = status_code
        self.headers = {}
        self._body = body
        self._content = content

    def json(self):
        if self._body is None:
            raise ValueError('no json')
        return self._body

    def iter_content(self, size):
        data = self._content or b''
        for i in range(0, len(data), size):
            yield data[i:i + size]

    def close(self):
        pass


class FakeGea:
    """Lo minimo de `external.py` de gea que usa este cliente."""

    def __init__(self):
        self.calls = []
        self.mode = 'ok'            # ok | down | 422 | revoke_down
        self.by_key = {}
        self.docs = {}
        self.revoked = []

    def __call__(self, method, url, headers=None, data=None, files=None,
                 timeout=None, verify=None, allow_redirects=None,
                 stream=False):
        self.calls.append({
            'method': method, 'url': url, 'headers': dict(headers or {}),
            'data': dict(data or {}), 'files': files, 'timeout': timeout,
            'verify': verify, 'allow_redirects': allow_redirects,
        })
        if self.mode == 'down' or (
                self.mode == 'revoke_down' and url.endswith('/revoke/')):
            # El texto lleva la URL y la clave a proposito: no debe salir.
            raise requests.ConnectionError(
                f'boom {url} {(headers or {}).get("X-Issuer-Key")}')

        if self.mode == 'redirect':
            response = FakeResponse(301)
            response.headers['Location'] = 'https://geausa.propensionesabogados.com/api/certificates/external/'
            return response

        if headers.get('X-Issuer-Key') != KEY:
            return FakeResponse(403, {'error': 'forbidden'})

        if method == 'POST' and url == f'{BASE}/api/certificates/external/':
            if self.mode == '422':
                return FakeResponse(422, {'error': 'certification_failed'})
            key = data['idempotency_key']
            if key in self.by_key:
                return FakeResponse(200, self.by_key[key])
            source = files['source'][1]
            doc_id = str(uuid.uuid4())
            copy = source + b'\n%%GEA-STAMPED\n'
            body = {
                'document_id': doc_id,
                'code': 'AB12CD34EF56',
                'verification_url': f'https://gea.test/verify/{doc_id}/',
                'source_hash': hashlib.sha256(source).hexdigest(),
                'public_copy_hash': hashlib.sha256(copy).hexdigest(),
                'public_copy_url': f'{BASE}/api/certificates/external/'
                                   f'{doc_id}/public-copy/',
                'issued_at': '2026-09-30T10:00:00-05:00',
            }
            self.by_key[key] = body
            self.docs[doc_id] = copy
            return FakeResponse(201, body)

        match = re.fullmatch(
            re.escape(BASE) + r'/api/certificates/external/([0-9a-f-]{36})/'
            r'(public-copy|revoke)/', url)
        if match:
            doc_id, action = match.groups()
            if doc_id not in self.docs:
                return FakeResponse(404, {'error': 'not_found'})
            if action == 'public-copy' and method == 'GET':
                return FakeResponse(200, content=self.docs[doc_id])
            if action == 'revoke' and method == 'POST':
                self.revoked.append(doc_id)
                return FakeResponse(200, {'document_id': doc_id,
                                          'status': 'REVOKED'})
        return FakeResponse(404, {'error': 'not_found'})

    def issue_calls(self):
        return [c for c in self.calls
                if c['method'] == 'POST' and c['url'].endswith('/external/')]


class InlineThread:
    """`threading.Thread` que corre el objetivo al arrancar."""

    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self.target, self.args, self.kwargs = target, args, kwargs or {}

    def start(self):
        self.target(*self.args, **self.kwargs)


@override_settings(
    GEA_CERT_API_BASE=BASE, GEA_ISSUER_SLUG='propensiones',
    SERVER_KEY=KEY, PAZ_Y_SALVO_PUBLIC_BASE=PUBLIC,
    PAZ_Y_SALVO_MAX_ATTEMPTS=3,
)
class CertifiedBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_record = ClientModel.objects.create(
            identification='16484186', full_name='Carlos Giraldo',
            email='cliente16484186@example.test',
        )
        cls.case = CaseModel.objects.create(
            client=cls.client_record, service=Service.JUDICIAL,
            stage=Stage.FINISHED, subtype='Pensión de invalidez',
            case_number='2024-00123-00',
        )
        otro = ClientModel.objects.create(
            identification='77777777', full_name='Otra Persona',
            email='cliente77777777@example.test',
        )
        cls.otro_case = CaseModel.objects.create(
            client=otro, service=Service.CONCILIATION, stage=Stage.FINISHED)

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
            ('apps.project.case_manager.paz_y_salvo.'
             'threading.Thread', InlineThread),
            # En una prueba la conexion es la de la transaccion del test:
            # `close_old_connections()` la cerraria.
            ('apps.project.case_manager.paz_y_salvo.'
             'close_old_connections', lambda: None),
        ):
            p = mock.patch(target, replacement)
            p.start()
            self.addCleanup(p.stop)

        make_user('abogada', gestor=True)
        self.gestor = Client()
        login_as(self.gestor, 'abogada')
        self.toggle_url = reverse(
            'case_manager:gestor_case_toggle_settlement', args=[self.case.pk])

    def toggle(self):
        with self.captureOnCommitCallbacks(execute=True):
            return self.gestor.post(self.toggle_url)

    def document(self):
        return PazYSalvoDocumentModel.objects.filter(
            case=self.case).exclude(status=Status.REVOKED).get()

    def logged_in_client(self):
        """Un navegador que se identifico como el cliente."""
        browser = Client()
        identificarse(browser, '16484186')
        return browser


class AuthorizeAndCertifyTests(CertifiedBase):
    def test_autorizar_crea_un_documento_y_el_hilo_lo_certifica(self):
        antes = timezone.now()
        self.toggle()

        self.case.refresh_from_db()
        self.assertTrue(self.case.paz_y_salvo_authorized)
        self.assertGreaterEqual(self.case.paz_y_salvo_authorized_at, antes)

        self.assertEqual(PazYSalvoDocumentModel.objects.count(), 1)
        doc = self.document()
        self.assertEqual(doc.status, Status.CERTIFIED)
        self.assertEqual(doc.authorized_at, self.case.paz_y_salvo_authorized_at)
        self.assertEqual(doc.gea_code, 'AB12CD34EF56')
        self.assertTrue(doc.verification_url.startswith('https://gea.test/'))
        self.assertEqual(doc.reference_snapshot, '2024-00123-00')
        self.assertEqual(doc.attempts, 1)
        self.assertEqual(doc.last_error, '')
        self.assertIsNotNone(doc.certified_at)

    def test_sin_commit_no_se_lanza_nada(self):
        """El hilo va en `on_commit`: si la transaccion falla, no sale."""
        self.gestor.post(self.toggle_url)   # sin ejecutar los on_commit

        self.assertEqual(self.gea.calls, [])
        self.assertEqual(self.document().status, Status.PENDING)

    def test_los_pdf_viven_fuera_de_media_y_sin_url(self):
        from django.conf import settings
        self.toggle()
        doc = self.document()

        for campo in (doc.source_file, doc.public_copy_file):
            self.assertTrue(campo.name)
            self.assertTrue(campo.path.startswith(self.private))
            self.assertNotIn(str(settings.MEDIA_ROOT), campo.path)
            with self.assertRaises(ValueError):
                campo.url

        with doc.public_copy_file.open('rb') as handle:
            self.assertTrue(handle.read().endswith(b'%%GEA-STAMPED\n'))
        with open(doc.public_copy_file.path, 'rb') as handle:
            self.assertEqual(
                hashlib.sha256(handle.read()).hexdigest(),
                doc.public_copy_hash)

    def test_la_peticion_a_gea_cumple_el_contrato(self):
        self.toggle()
        doc = self.document()
        call = self.gea.issue_calls()[0]

        self.assertEqual(call['headers']['X-Issuer-Key'], KEY)
        self.assertEqual(call['data']['issuer'], 'propensiones')
        self.assertEqual(call['data']['idempotency_key'], doc.idempotency_key)
        self.assertEqual(
            call['data']['qr_payload'],
            f'{PUBLIC}/consultar/proceso/{self.case.pk}/paz-y-salvo/')
        self.assertEqual(call['files']['source'][2], 'application/pdf')
        self.assertTrue(call['files']['source'][1].startswith(b'%PDF'))
        # TLS verificado, timeout puesto, sin redirecciones.
        self.assertIs(call['verify'], True)
        self.assertIsNotNone(call['timeout'])
        self.assertIs(call['allow_redirects'], False)

    def test_formato_del_codigo_de_barras(self):
        self.toggle()
        doc = self.document()
        texto = self.gea.issue_calls()[0]['data']['barcode_text']

        dia = timezone.localtime(doc.authorized_at).strftime('%Y%m%d')
        self.assertEqual(texto, f'{str(self.case.pk)[:8]} {dia} 901409813-7')
        # Lo que acepta el validador de gea.
        self.assertRegex(texto, r'^[A-Za-z0-9 ._\-]+$')
        self.assertNotIn('//', texto)
        self.assertLessEqual(len(texto), 48)

    def test_el_barcode_text_usa_la_fecha_de_bogota(self):
        # 03:30 UTC del 1 de octubre son las 22:30 del 30 de septiembre.
        instante = datetime(2026, 10, 1, 3, 30, tzinfo=dt_timezone.utc)
        self.assertEqual(
            paz_y_salvo.barcode_text(self.case.pk, instante),
            f'{str(self.case.pk)[:8]} 20260930 901409813-7')

    def test_placement_y_pdf_sin_codigos(self):
        self.toggle()
        call = self.gea.issue_calls()[0]
        placement = json.loads(call['data']['placement'])
        reader = PdfReader(io.BytesIO(call['files']['source'][1]))

        self.assertEqual(len(reader.pages), 1)
        page = reader.pages[0]
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        self.assertAlmostEqual(width, 595.28, places=1)      # A4

        # Solo el logo y la firma: ni QR ni codigo de barras todavia.
        self.assertEqual(len(page.images), 2)

        qr, bar = placement['qr'], placement['barcode']
        self.assertEqual(qr['page'], 1)
        self.assertEqual(bar['page'], 1)
        self.assertLessEqual(qr['x'] + qr['size'], width)
        self.assertLessEqual(qr['y'] + qr['size'], height)
        self.assertLessEqual(bar['x'] + bar['width'], width)
        self.assertGreaterEqual(min(qr['x'], qr['y'], bar['x'], bar['y']), 0)

        # QR a la altura del logo: mismo centro vertical.
        _, logo_y, _, logo_h = paz_y_salvo_pdf._logo_box()
        self.assertAlmostEqual(qr['y'] + qr['size'] / 2, logo_y + logo_h / 2,
                               delta=1)

        # Codigo de barras entre "PROPENSIONES S.A.S." y la descripcion de la
        # entidad: donde estaba el NIT.
        posiciones = {}

        def visitor(text, cm, tm, font_dict, font_size):
            if text.strip():
                posiciones[text.strip()] = tm[5]

        page.extract_text(visitor_text=visitor)
        empresa = posiciones['PROPENSIONES S.A.S.']
        entidad = next(y for t, y in posiciones.items()
                       if t.startswith('Entidad Privada'))
        self.assertGreater(bar['y'], entidad)
        self.assertLess(bar['y'] + bar['height'], empresa)

        # El hueco esta vacio: no hay texto dentro del rectangulo del codigo.
        for texto, y in posiciones.items():
            self.assertFalse(
                bar['y'] < y < bar['y'] + bar['height'], texto)

    def test_el_pdf_lleva_los_datos_y_la_fecha_congelada(self):
        instante = datetime(2026, 3, 5, 15, 0, tzinfo=dt_timezone.utc)
        pdf = paz_y_salvo_pdf.build_pdf(
            case=self.case, authorized_at=instante, reference='2024-00123-00')
        texto = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()

        self.assertIn('Carlos Giraldo', texto)
        self.assertIn('16.484.186', texto)
        self.assertIn('A PAZ Y SALVO', texto)
        self.assertIn('5 días del mes de marzo de 2026', texto)
        self.assertIn(str(self.case.pk)[:8], texto)
        self.assertIn('2024-00123-00', texto)
        self.assertIn('Pensión de invalidez', texto)
        self.assertNotIn('901.409.813-7', texto)

    def test_el_pdf_de_un_cliente_nit_lleva_su_nit(self):
        empresa = ClientModel.objects.create(
            identification='900123456', verification_digit='7',
            identification_type='NIT', full_name='Constructora Andina SAS',
            email='empresa@example.test')
        case = CaseModel.objects.create(
            client=empresa, service=Service.JUDICIAL, stage=Stage.FINISHED)
        pdf = paz_y_salvo_pdf.build_pdf(
            case=case, authorized_at=timezone.now(), reference='—')
        texto = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()

        self.assertIn('900.123.456-7', texto)
        self.assertIn('persona jurídica', texto)

    def test_volver_a_autorizar_crea_un_documento_nuevo(self):
        self.toggle()
        primero = self.document()

        self.toggle()                       # retirar
        primero.refresh_from_db()
        self.assertEqual(primero.status, Status.REVOKED)
        self.assertIsNotNone(primero.revoked_at)
        self.assertEqual(self.gea.revoked, [primero.gea_document_id])
        self.assertTrue(primero.gea_revoked)
        self.case.refresh_from_db()
        self.assertFalse(self.case.paz_y_salvo_authorized)
        self.assertIsNone(self.case.paz_y_salvo_authorized_at)

        self.toggle()                       # volver a autorizar
        segundo = self.document()
        self.assertNotEqual(primero.pk, segundo.pk)
        self.assertNotEqual(primero.idempotency_key, segundo.idempotency_key)
        self.assertNotEqual(primero.gea_document_id, segundo.gea_document_id)
        self.assertEqual(segundo.status, Status.CERTIFIED)
        self.assertEqual(PazYSalvoDocumentModel.objects.count(), 2)

    def test_solo_un_documento_vigente_por_caso(self):
        self.toggle()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PazYSalvoDocumentModel.objects.create(
                case=self.case, authorized_at=timezone.now(),
                idempotency_key='otra')

    def test_desmarcar_la_casilla_por_otra_via_tambien_revoca(self):
        """Formulario del asunto o admin: mismo efecto que el boton."""
        with self.captureOnCommitCallbacks(execute=True):
            self.case.paz_y_salvo_authorized = True
            self.case.save()
            paz_y_salvo.sync_authorization(self.case, False)
        self.assertEqual(self.document().status, Status.CERTIFIED)

        with self.captureOnCommitCallbacks(execute=True):
            self.case.paz_y_salvo_authorized = False
            self.case.save()
            paz_y_salvo.sync_authorization(self.case, True)
        self.assertEqual(
            PazYSalvoDocumentModel.objects.get().status, Status.REVOKED)


class FailureAndRetryTests(CertifiedBase):
    def test_redireccion_guarda_destino_en_espanol_sin_seguirla(self):
        self.gea.mode = 'redirect'
        self.toggle()
        doc = self.document()
        self.assertEqual(doc.status, Status.FAILED)
        self.assertEqual(doc.last_error,
            'gea redirige a https://geausa.propensionesabogados.com/api/certificates/external/: revisa GEA_CERT_API_BASE')
        self.assertEqual(len(self.gea.calls), 1)
        self.assertIs(self.gea.calls[0]['allow_redirects'], False)

    def test_todos_los_3xx_y_destinos_sin_clave(self):
        from .. import gea_client
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                response = FakeResponse(status)
                response.headers['Location'] = 'https://gea.test/' + KEY
                error = str(gea_client._error_from(response))
                self.assertIn('gea redirige a https://gea.test/***', error)
                self.assertNotIn(KEY, error)
                response.headers.clear()
                self.assertIn('sin destino Location', str(gea_client._error_from(response)))

    def test_gea_caido_deja_failed_y_la_autorizacion_sigue(self):
        self.gea.mode = 'down'
        with self.assertLogs(level='WARNING') as logs:
            self.toggle()

        self.case.refresh_from_db()
        self.assertTrue(self.case.paz_y_salvo_authorized)
        doc = self.document()
        self.assertEqual(doc.status, Status.FAILED)
        self.assertIn('No se pudo conectar con gea', doc.last_error)
        self.assertEqual(doc.attempts, 1)
        # Ni el error guardado ni los logs llevan la clave.
        self.assertNotIn(KEY, doc.last_error)
        self.assertNotIn(KEY, '\n'.join(logs.output))
        self.assertNotIn('gea.test', doc.last_error)

    def test_422_deja_failed_con_el_error(self):
        self.gea.mode = '422'
        self.toggle()

        doc = self.document()
        self.assertEqual(doc.status, Status.FAILED)
        self.assertIn('422', doc.last_error)

    def test_el_comando_reintenta_con_la_misma_clave_y_certifica(self):
        self.gea.mode = 'down'
        self.toggle()
        doc = self.document()
        clave = doc.idempotency_key
        self.assertEqual(doc.status, Status.FAILED)

        self.gea.mode = 'ok'
        salida = StringIO()
        call_command('certify_pending_paz_y_salvo', stdout=salida)

        doc.refresh_from_db()
        self.assertEqual(doc.status, Status.CERTIFIED)
        self.assertEqual(doc.idempotency_key, clave)
        self.assertEqual(doc.last_error, '')
        self.assertEqual(doc.attempts, 2)
        self.assertEqual(
            {c['data']['idempotency_key'] for c in self.gea.issue_calls()},
            {clave})
        self.assertIn('Certificados: 1', salida.getvalue())

    def test_reintentar_no_duplica_en_gea(self):
        """Si gea ya lo tenia (la respuesta se perdio), devuelve el mismo."""
        self.toggle()
        doc = self.document()
        PazYSalvoDocumentModel.objects.filter(pk=doc.pk).update(
            status=Status.FAILED, gea_document_id='', gea_code='')

        call_command('certify_pending_paz_y_salvo', stdout=StringIO())

        doc.refresh_from_db()
        self.assertEqual(doc.status, Status.CERTIFIED)
        self.assertEqual(len(self.gea.docs), 1)
        self.assertEqual(len(self.gea.by_key), 1)

    def test_el_comando_respeta_el_maximo_de_intentos(self):
        self.gea.mode = 'down'
        self.toggle()                                     # intento 1
        for _ in range(4):
            call_command('certify_pending_paz_y_salvo',
                         stdout=StringIO(), stderr=StringIO())

        self.assertEqual(self.document().attempts, 3)     # tope
        self.assertEqual(len(self.gea.issue_calls()), 3)

        salida = StringIO()
        self.gea.mode = 'ok'
        call_command('certify_pending_paz_y_salvo', '--force', stdout=salida)
        self.assertEqual(self.document().status, Status.CERTIFIED)

    def test_el_comando_acepta_case(self):
        self.gea.mode = 'down'
        self.toggle()
        self.gea.mode = 'ok'

        call_command('certify_pending_paz_y_salvo',
                     '--case', str(self.otro_case.pk), stdout=StringIO())
        self.assertEqual(self.document().status, Status.FAILED)

        call_command('certify_pending_paz_y_salvo',
                     '--case', str(self.case.pk), stdout=StringIO())
        self.assertEqual(self.document().status, Status.CERTIFIED)

    @override_settings(GEA_CERT_API_BASE='', SERVER_KEY='')
    def test_sin_configurar_queda_pending_sin_llamar_a_nadie(self):
        self.toggle()

        doc = self.document()
        self.assertEqual(doc.status, Status.PENDING)
        self.assertIn('no está configurado', doc.last_error)
        self.assertEqual(doc.attempts, 0)
        self.assertEqual(self.gea.calls, [])
        self.case.refresh_from_db()
        self.assertTrue(self.case.paz_y_salvo_authorized)

    def test_revocar_con_gea_caido_se_completa_con_el_comando(self):
        self.toggle()
        doc = self.document()
        self.gea.mode = 'revoke_down'

        self.toggle()                                     # retirar
        doc.refresh_from_db()
        self.assertEqual(doc.status, Status.REVOKED)
        self.assertFalse(doc.gea_revoked)
        self.assertIn('Revocación pendiente', doc.last_error)
        self.assertNotIn(KEY, doc.last_error)

        self.gea.mode = 'ok'
        call_command('certify_pending_paz_y_salvo', stdout=StringIO())
        doc.refresh_from_db()
        self.assertTrue(doc.gea_revoked)
        self.assertEqual(self.gea.revoked, [doc.gea_document_id])

    def test_retirado_mientras_se_certifica_se_revoca_en_gea(self):
        """La carrera: gea ya emitio cuando llega la revocacion local."""
        real_download = paz_y_salvo.gea_client.download_public_copy

        def descargar_y_retirar(document_id, expected_hash=''):
            copia = real_download(document_id, expected_hash)
            PazYSalvoDocumentModel.objects.update(status=Status.REVOKED)
            return copia

        with mock.patch.object(paz_y_salvo.gea_client, 'download_public_copy',
                               descargar_y_retirar):
            self.toggle()

        doc = PazYSalvoDocumentModel.objects.get()
        self.assertEqual(doc.status, Status.REVOKED)
        self.assertFalse(doc.public_copy_file)
        self.assertTrue(doc.gea_revoked)
        self.assertEqual(len(self.gea.revoked), 1)


class PublicViewTests(CertifiedBase):
    def setUp(self):
        super().setUp()
        self.toggle()
        self.doc = self.document()
        # Una fecha de autorizacion que no es la de hoy.
        self.fecha = datetime(2026, 3, 5, 15, 0, tzinfo=dt_timezone.utc)
        PazYSalvoDocumentModel.objects.filter(pk=self.doc.pk).update(
            authorized_at=self.fecha)
        self.url = reverse('case_manager:paz_y_salvo', args=[self.case.pk])

    def test_el_cliente_ve_el_documento_con_la_fecha_congelada(self):
        respuesta = self.logged_in_client().get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Carlos Giraldo')
        self.assertContains(respuesta, '05/03/2026')
        self.assertContains(respuesta, str(self.case.pk)[:8])
        self.assertContains(
            respuesta,
            reverse('case_manager:paz_y_salvo_download', args=[self.case.pk]))
        self.assertNotContains(
            respuesta, timezone.localtime().strftime('%d/%m/%Y'))
        self.assertNotIn('901.409.813-7', respuesta.content.decode())

    def test_sin_certificar_el_cliente_no_ve_el_boton_de_descarga(self):
        PazYSalvoDocumentModel.objects.filter(pk=self.doc.pk).update(
            status=Status.PENDING)

        respuesta = self.logged_in_client().get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(
            respuesta,
            reverse('case_manager:paz_y_salvo_download', args=[self.case.pk]))

    def test_el_anonimo_ve_una_verificacion_sin_datos_personales(self):
        respuesta = Client().get(self.url)
        html = respuesta.content.decode()

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('esValidoPS', html)
        for text in ('Paz y salvo válido', 'Emitido el', 'Emitido por', 'Verificar el certificado'):
            self.assertIn(text, html)
        self.assertIn('05/03/2026', html)
        self.assertIn(str(self.case.pk)[:8], html)
        self.assertIn('2024-00123-00', html)
        self.assertIn('Propensiones Abogados', html)
        self.assertIn(self.doc.verification_url, html)
        for prohibido in ('Carlos Giraldo', '16484186', '16.484.186',
                          'cliente16484186@example.test', 'Giraldo'):
            self.assertNotIn(prohibido, html)
        self.assertIn('noindex', respuesta['X-Robots-Tag'])
        self.assertIn('no-store', respuesta['Cache-Control'])

    def test_el_anonimo_ve_revocado_y_sin_enlace_de_gea(self):
        self.toggle()                                     # retirar

        html = Client().get(self.url).content.decode()

        self.assertIn('esRevocadoPS', html)
        self.assertIn('Paz y salvo revocado', html)
        self.assertNotIn('esValidoPS', html)
        self.assertNotIn(self.doc.verification_url, html)
        self.assertNotIn('Carlos Giraldo', html)

    def test_un_cliente_ajeno_ve_solo_la_verificacion(self):
        ajeno = Client()
        identificarse(ajeno, '77777777')

        html = ajeno.get(self.url).content.decode()

        self.assertIn('esValidoPS', html)
        for text in ('Paz y salvo válido', 'Emitido el', 'Emitido por', 'Verificar el certificado'):
            self.assertIn(text, html)
        self.assertNotIn('Carlos Giraldo', html)

    def test_sin_paz_y_salvo_o_inexistente_es_el_mismo_404(self):
        sin_paz = Client().get(
            reverse('case_manager:paz_y_salvo', args=[self.otro_case.pk]))
        inexistente = Client().get(
            reverse('case_manager:paz_y_salvo', args=[uuid.uuid4()]))

        self.assertEqual(sin_paz.status_code, 404)
        self.assertEqual(inexistente.status_code, 404)
        self.assertEqual(sin_paz.content, inexistente.content)


class DownloadTests(CertifiedBase):
    def setUp(self):
        super().setUp()
        self.toggle()
        self.doc = self.document()
        self.url = reverse('case_manager:paz_y_salvo_download',
                           args=[self.case.pk])

    def test_el_cliente_baja_la_copia_como_adjunto(self):
        respuesta = self.logged_in_client().get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertIn('attachment', respuesta['Content-Disposition'])
        self.assertIn(str(self.case.pk)[:8], respuesta['Content-Disposition'])
        self.assertIn('no-store', respuesta['Cache-Control'])
        cuerpo = b''.join(respuesta.streaming_content)
        self.assertEqual(hashlib.sha256(cuerpo).hexdigest(),
                         self.doc.public_copy_hash)

    def test_el_gestor_tambien_la_baja(self):
        respuesta = self.gestor.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        list(respuesta.streaming_content)

    def test_los_demas_reciben_404(self):
        # Anonimo.
        self.assertEqual(Client().get(self.url).status_code, 404)

        # Otro cliente identificado.
        ajeno = Client()
        identificarse(ajeno, '77777777')
        self.assertEqual(ajeno.get(self.url).status_code, 404)

        # Usuario con sesion pero fuera del grupo del gestor.
        make_user('externo')
        otro = Client()
        login_as(otro, 'externo')
        self.assertEqual(otro.get(self.url).status_code, 404)

        # Caso ajeno / inexistente, incluso para el gestor.
        for pk in (self.otro_case.pk, uuid.uuid4()):
            self.assertEqual(self.gestor.get(reverse(
                'case_manager:paz_y_salvo_download', args=[pk])).status_code,
                404)

    def test_sin_certificar_o_revocado_es_404(self):
        cliente = self.logged_in_client()
        PazYSalvoDocumentModel.objects.filter(pk=self.doc.pk).update(
            status=Status.FAILED)
        self.assertEqual(cliente.get(self.url).status_code, 404)

        PazYSalvoDocumentModel.objects.filter(pk=self.doc.pk).update(
            status=Status.CERTIFIED)
        self.assertEqual(cliente.get(self.url).status_code, 200)

        self.toggle()                                     # retirar
        self.assertEqual(cliente.get(self.url).status_code, 404)
        self.assertEqual(self.gestor.get(self.url).status_code, 404)

    def test_el_fichero_no_se_sirve_por_media(self):
        from django.conf import settings
        self.assertFalse(self.doc.public_copy_file.path.startswith(
            str(settings.MEDIA_ROOT)))
        self.assertEqual(Client().get(
            '/media/' + self.doc.public_copy_file.name).status_code, 404)


class GestorTests(CertifiedBase):
    def test_autorizar_y_revocar_desde_la_vista(self):
        # Produccion es MySQL/MariaDB: la vista no debe usar `FOR UPDATE OF`.
        # (Simular el backend en SQLite no es realista: el compilador
        # emitiria `FOR UPDATE` y SQLite lo rechazaria; ver test_db_portability.)
        respuesta = self.toggle()
        self.assertEqual(respuesta.status_code, 302)
        self.case.refresh_from_db()
        self.assertTrue(self.case.paz_y_salvo_authorized)
        self.assertEqual(self.document().status, Status.CERTIFIED)

        respuesta = self.toggle()
        self.assertEqual(respuesta.status_code, 302)
        self.case.refresh_from_db()
        self.assertFalse(self.case.paz_y_salvo_authorized)
        self.assertFalse(PazYSalvoDocumentModel.objects.filter(
            case=self.case).exclude(status=Status.REVOKED).exists())

    def ficha(self):
        return self.gestor.get(
            reverse('case_manager:gestor_case_update', args=[self.case.pk]))

    def test_la_ficha_ensena_el_estado_certificado(self):
        self.toggle()
        doc = self.document()

        respuesta = self.ficha()

        self.assertContains(respuesta, 'data-paz-y-salvo-status')
        self.assertContains(respuesta, 'Certificado')
        for text in ('Paz y salvo certificado', 'Estado', 'Autorizado el', 'Descargar copia distribuible'):
            self.assertContains(respuesta, text)
        self.assertNotContains(respuesta, 'Certified settlement letter')
        self.assertContains(respuesta, doc.gea_code)
        self.assertContains(respuesta, doc.verification_url)
        self.assertContains(
            respuesta,
            reverse('case_manager:paz_y_salvo_download', args=[self.case.pk]))
        self.assertNotContains(respuesta, 'retry-certification-form')
        self.assertNotIn(KEY, respuesta.content.decode())

    def test_la_ficha_ensena_el_fallo_y_el_boton_de_reintento(self):
        self.gea.mode = 'down'
        self.toggle()

        respuesta = self.ficha()

        self.assertContains(respuesta, 'Fallido')
        self.assertContains(respuesta, 'Reintentar certificación')
        self.assertContains(respuesta, 'No se pudo conectar con gea')
        self.assertContains(respuesta, 'retry-certification-form')
        self.assertContains(respuesta, reverse(
            'case_manager:gestor_case_retry_certification',
            args=[self.case.pk]))
        self.assertNotIn(KEY, respuesta.content.decode())

    def test_reintentar_certifica(self):
        self.gea.mode = 'down'
        self.toggle()
        self.gea.mode = 'ok'

        respuesta = self.gestor.post(reverse(
            'case_manager:gestor_case_retry_certification',
            args=[self.case.pk]))

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.document().status, Status.CERTIFIED)

    def test_reintentar_pide_permiso_y_csrf(self):
        self.gea.mode = 'down'
        self.toggle()
        self.gea.mode = 'ok'
        url = reverse('case_manager:gestor_case_retry_certification',
                      args=[self.case.pk])

        # Sin sesion.
        Client().post(url)
        # Con sesion pero sin el grupo.
        make_user('externo')
        otro = Client()
        login_as(otro, 'externo')
        self.assertIn(otro.post(url).status_code, (302, 403, 404))
        # El cliente identificado tampoco.
        self.logged_in_client().post(url)
        # Un GET no hace nada.
        self.assertEqual(self.gestor.get(url).status_code, 405)
        # Sin token CSRF.
        estricto = Client(enforce_csrf_checks=True)
        login_as(estricto, 'abogada')
        self.assertEqual(estricto.post(url).status_code, 403)

        self.assertEqual(self.document().status, Status.FAILED)
        self.assertEqual(len(self.gea.issue_calls()), 1)

    def test_reintentar_sin_configurar_avisa(self):
        self.gea.mode = 'down'
        self.toggle()

        with override_settings(GEA_CERT_API_BASE=''):
            self.gestor.post(reverse(
                'case_manager:gestor_case_retry_certification',
                args=[self.case.pk]))

        self.assertEqual(self.document().status, Status.FAILED)
        self.assertEqual(len(self.gea.issue_calls()), 1)


class SpanishStatusTests(TestCase):
    def test_estados_en_espanol(self):
        from django.utils.translation import override
        with override('es'):
            for status, label in ((Status.PENDING, 'Pendiente'),
                                  (Status.CERTIFIED, 'Certificado'),
                                  (Status.FAILED, 'Fallido'),
                                  (Status.REVOKED, 'Revocado')):
                self.assertEqual(PazYSalvoDocumentModel(status=status).get_status_display(), label)


class AdminDocumentTests(CertifiedBase):
    """
    El admin de solo lectura no puede pedir `.url` a ficheros privados.

    Antes pintaba `<a href=value.url>` y la ficha reventaba con un 500
    ('Private files have no public URL.').
    """

    def setUp(self):
        super().setUp()
        self.toggle()
        self.doc = self.document()
        make_user('jefe', superuser=True)
        self.admin = Client()
        login_as(self.admin, 'jefe')

    def change_url(self, doc):
        return reverse(
            'admin:case_manager_pazysalvodocumentmodel_change',
            args=[doc.pk])

    def test_la_ficha_se_abre_con_nombre_y_enlace_de_descarga(self):
        self.assertTrue(self.doc.source_file)
        self.assertTrue(self.doc.public_copy_file)

        respuesta = self.admin.get(self.change_url(self.doc))
        html = respuesta.content.decode()

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(os.path.basename(self.doc.source_file.name), html)
        self.assertIn(os.path.basename(self.doc.public_copy_file.name), html)
        self.assertIn(reverse(
            'case_manager:paz_y_salvo_download', args=[self.case.pk]), html)
        self.assertNotIn('/media/', html)

    def test_el_original_interno_no_lleva_enlace(self):
        html = self.admin.get(self.change_url(self.doc)).content.decode()
        nombre = os.path.basename(self.doc.source_file.name)

        self.assertNotIn(f'>{nombre}</a>', html)

    def test_el_gestor_tambien_la_abre(self):
        make_user('staffgestor', staff=True, gestor=True)
        gestor = Client()
        login_as(gestor, 'staffgestor')

        self.assertEqual(
            gestor.get(self.change_url(self.doc)).status_code, 200)

    def test_un_documento_revocado_muestra_el_nombre_sin_enlace(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.gestor.post(self.toggle_url)   # retira el paz y salvo
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, Status.REVOKED)

        respuesta = self.admin.get(self.change_url(self.doc))
        html = respuesta.content.decode()

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(os.path.basename(self.doc.public_copy_file.name), html)
        self.assertNotIn(reverse(
            'case_manager:paz_y_salvo_download', args=[self.case.pk]), html)

    def test_el_listado_se_abre(self):
        respuesta = self.admin.get(reverse(
            'admin:case_manager_pazysalvodocumentmodel_changelist'))

        self.assertEqual(respuesta.status_code, 200)

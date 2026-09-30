"""
El receptor de informes de la CSP: apunta en el log, no guarda nada, tiene
cupo y no apunta secretos.
"""

import json

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from apps.common.utils import csp_report
from apps.common.utils.models import IPBlockedModel

URL = reverse('csp_report')

REPORT = {
    'csp-report': {
        'document-uri': 'https://propensionesabogados.com/account/reset/'
                        'MjE/c9x-4f7b2a1d9e8c7b6a5d4c3b2a1f0e9d8c/?next=/x',
        'violated-directive': 'script-src-elem',
        'effective-directive': 'script-src-elem',
        'blocked-uri': 'inline',
        'source-file': 'https://propensionesabogados.com/x?token=secreto',
        'line-number': 12,
        'disposition': 'report',
    }
}


def post(client, payload, content_type='application/csp-report'):
    body = payload if isinstance(payload, (bytes, str)) else json.dumps(payload)
    return client.post(URL, body, content_type=content_type)


class CspReportTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_un_informe_se_apunta_y_contesta_204(self):
        with self.assertLogs('csp_report', 'WARNING') as log:
            response = post(self.client, REPORT)

        self.assertEqual(response.status_code, 204)
        linea = '\n'.join(log.output)
        self.assertIn('script-src-elem', linea)
        self.assertIn('inline', linea)

    def test_no_apunta_tokens_ni_query(self):
        with self.assertLogs('csp_report', 'WARNING') as log:
            post(self.client, REPORT)

        linea = '\n'.join(log.output)
        self.assertNotIn('c9x-4f7b2a1d', linea)
        self.assertNotIn('secreto', linea)
        self.assertNotIn('next=', linea)
        # Del enlace solo queda el origen y la forma de la ruta.
        self.assertIn('https://propensionesabogados.com/account/reset/', linea)
        self.assertNotIn('/reset/MjE/c9x', linea)

    def test_un_data_uri_no_se_apunta_entero(self):
        report = {'csp-report': {
            **REPORT['csp-report'],
            'blocked-uri': 'data:text/html;base64,SECRETO'}}

        with self.assertLogs('csp_report', 'WARNING') as log:
            post(self.client, report)

        self.assertNotIn('SECRETO', '\n'.join(log.output))

    def test_formato_nuevo_reports_json(self):
        payload = [{'type': 'csp-violation', 'body': {
            'effectiveDirective': 'img-src',
            'blockedURL': 'https://ejemplo.test/a.png',
            'documentURL': 'https://propensionesabogados.com/'}}]

        with self.assertLogs('csp_report', 'WARNING') as log:
            response = post(self.client, payload,
                            content_type='application/reports+json')

        self.assertEqual(response.status_code, 204)
        self.assertIn('img-src', '\n'.join(log.output))

    def test_no_guarda_nada_en_base(self):
        antes = IPBlockedModel.objects.count()

        post(self.client, REPORT)

        self.assertEqual(IPBlockedModel.objects.count(), antes)

    def test_basura_contesta_204_y_no_apunta(self):
        with self.assertNoLogs('csp_report', 'WARNING'):
            for cuerpo in (b'no es json', b'[]', b'{"a": 1}', b'null'):
                self.assertEqual(post(self.client, cuerpo).status_code, 204)

    def test_un_cuerpo_desmedido_se_descarta(self):
        grande = json.dumps({'csp-report': {'blocked-uri': 'x' * 20_000}})

        with self.assertNoLogs('csp_report', 'WARNING'):
            self.assertEqual(post(self.client, grande).status_code, 204)

    def test_solo_admite_post(self):
        self.assertEqual(self.client.get(URL).status_code, 405)

    def test_tiene_cupo_por_ip(self):
        limite = csp_report.csp_report_ip.limit

        with self.assertLogs('csp_report', 'WARNING') as log:
            for _ in range(limite + 5):
                self.assertEqual(post(self.client, REPORT).status_code, 204)

        # El resto se descarto sin apuntar.
        self.assertEqual(len(log.output), limite)

    def test_no_pide_csrf(self):
        self.assertEqual(
            post(Client(enforce_csrf_checks=True), REPORT).status_code, 204)

"""
Las notas del asunto: se ven todas, y cada una se puede mostrar u ocultar en
el portal del cliente despues de creada.

Dos cosas que se cuidan aqui:

1. **Que no se pierda ninguna nota.** Se comprueba en las tres pantallas del
   gestor donde hay que verlas --la ficha del asunto, la del cliente y el
   listado-- con mas de una nota.
2. **Que cambiar la visibilidad no avise a nadie.** Si la nota se mando por
   correo, el cambio no reenvia nada ni toca `notified_at`.
"""

import os
from datetime import timedelta
from io import StringIO
from pathlib import Path

from auditlog.models import LogEntry
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from ..choices import NoteKind
from ..models import CaseNoteModel
from .test_access import login_as, make_user
from .test_notes import make_case
from .test_public_access import identificarse

FETCH = {'HTTP_X_REQUESTED_WITH': 'fetch'}


def add_notes(case, count, **extra):
    """`count` notas, la 0 la mas antigua y la ultima la mas reciente."""
    base = timezone.now() - timedelta(days=count)
    notes = []
    for index in range(count):
        note = CaseNoteModel.objects.create(
            case=case, kind=NoteKind.INFO, title=f'Novedad {index}',
            body=f'Cuerpo {index}', **extra,
        )
        CaseNoteModel.objects.filter(pk=note.pk).update(
            created=base + timedelta(days=index)
        )
        notes.append(note)
    return notes


class AllNotesAreShownTests(TestCase):
    """Con 2, 3, 4... notas se ven todas, de la mas reciente a la mas antigua."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cls.case = make_case()
        cls.notes = add_notes(cls.case, 6)

    def setUp(self):
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')

    def test_la_ficha_del_asunto_las_pinta_todas_y_en_orden(self):
        response = self.client.get(
            reverse('case_manager:gestor_case_update', args=[self.case.pk])
        )
        html = response.content.decode()

        for index in range(6):
            self.assertIn(f'Novedad {index}', html)
        positions = [html.index(f'Novedad {i}') for i in (5, 4, 3, 2, 1, 0)]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(html.count('data-note-visibility data-unsaved-skip'), 6)
        self.assertContains(response, 'data-notes-list')
        self.assertContains(response, 'id="notas"')

    def test_el_contador_dice_cuantas_hay(self):
        response = self.client.get(
            reverse('case_manager:gestor_case_update', args=[self.case.pk])
        )
        self.assertContains(response, '<span class="badge text-bg-light ms-1" data-notes-count>6</span>', html=False)

    def test_la_ficha_del_cliente_muestra_todas_las_notas_de_cada_asunto(self):
        """Antes las cargaba (`prefetch_related`) y no las pintaba."""
        response = self.client.get(
            reverse('case_manager:gestor_client_detail',
                    args=[self.case.client.pk])
        )
        for index in range(6):
            self.assertContains(response, f'Novedad {index}')
        self.assertContains(response, f'data-case-notes="{self.case.pk}"')

    def test_la_ficha_del_cliente_no_hace_una_consulta_por_asunto(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        url = reverse('case_manager:gestor_client_detail',
                      args=[self.case.client.pk])
        with CaptureQueriesContext(connection) as one:
            self.client.get(url)
        for _ in range(3):
            add_notes(self.other_case(), 2)
        with CaptureQueriesContext(connection) as several:
            self.client.get(url)
        self.assertEqual(len(one), len(several))

    def other_case(self):
        from ..models import CaseModel
        return CaseModel.objects.create(
            client=self.case.client, service=self.case.service,
        )

    def test_el_listado_dice_cuantas_notas_lleva_cada_asunto(self):
        response = self.client.get(reverse('case_manager:gestor_case_list'))
        self.assertContains(response, 'data-note-count="6"')

    def test_el_portal_muestra_todas_las_visibles(self):
        self.client.logout()
        response = identificarse(self.client)
        for index in range(6):
            self.assertContains(response, f'Novedad {index}')


class NoteVisibilityToggleTests(TestCase):
    """Cambiar quien ve una nota que ya existe."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_case_manager_group', stdout=StringIO())
        cls.case = make_case()

    def setUp(self):
        mail.outbox = []
        self.note = CaseNoteModel.objects.create(
            case=self.case, kind=NoteKind.INFO, title='Audiencia fijada',
            body='Sera el lunes.', visible_to_client=True,
            notified_at=timezone.now() - timedelta(days=1),
        )
        self.notified_at = self.note.notified_at
        make_user('abogada', gestor=True)
        login_as(self.client, 'abogada')
        self.url = reverse(
            'case_manager:gestor_case_note_visibility',
            args=[self.case.pk, self.note.pk],
        )

    def portal(self):
        client = Client()
        return identificarse(client)

    def test_ocultar_con_fetch_devuelve_json_y_guarda(self):
        response = self.client.post(self.url, {'visible': '0'}, **FETCH)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['visible'], False)
        self.note.refresh_from_db()
        self.assertFalse(self.note.visible_to_client)

    def test_ocultar_la_quita_del_portal_y_mostrar_la_devuelve(self):
        self.assertContains(self.portal(), 'Audiencia fijada')

        self.client.post(self.url, {'visible': '0'}, **FETCH)
        self.assertNotContains(self.portal(), 'Audiencia fijada')

        self.client.post(self.url, {'visible': '1'}, **FETCH)
        self.assertContains(self.portal(), 'Audiencia fijada')

    def test_una_casilla_sin_marcar_no_manda_nada_y_es_interna(self):
        """El envio sin JavaScript: la casilla desmarcada no viaja."""
        self.client.post(self.url, {})

        self.note.refresh_from_db()
        self.assertFalse(self.note.visible_to_client)

    def test_sin_fetch_redirige_a_la_ficha_con_aviso(self):
        response = self.client.post(self.url, {'visible': '0'})

        self.assertRedirects(
            response,
            reverse('case_manager:gestor_case_update', args=[self.case.pk])
            + '#notas',
            fetch_redirect_response=False,
        )

    def test_no_reenvia_ni_toca_la_fecha_del_aviso(self):
        self.client.post(self.url, {'visible': '0'}, **FETCH)
        self.client.post(self.url, {'visible': '1'}, **FETCH)

        self.assertEqual(len(mail.outbox), 0)
        self.note.refresh_from_db()
        self.assertEqual(self.note.notified_at, self.notified_at)

    def test_deja_rastro_en_auditlog(self):
        self.client.post(self.url, {'visible': '0'}, **FETCH)

        entry = LogEntry.objects.get_for_object(self.note).first()
        self.assertIsNotNone(entry)
        self.assertIn('visible_to_client', entry.changes_dict)
        self.assertEqual(entry.actor.username, 'abogada')

    def test_solo_admite_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_sin_sesion_no_se_puede(self):
        self.client.logout()

        response = self.client.post(self.url, {'visible': '0'}, **FETCH)

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])
        self.note.refresh_from_db()
        self.assertTrue(self.note.visible_to_client)

    def test_sin_el_grupo_da_404_y_no_cambia_nada(self):
        self.client.logout()
        make_user('intruso')
        login_as(self.client, 'intruso')

        response = self.client.post(self.url, {'visible': '0'}, **FETCH)

        self.assertEqual(response.status_code, 404)
        self.note.refresh_from_db()
        self.assertTrue(self.note.visible_to_client)

    def test_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        login_as(client, 'abogada')

        response = client.post(self.url, {'visible': '0'}, **FETCH)

        self.assertEqual(response.status_code, 403)
        self.note.refresh_from_db()
        self.assertTrue(self.note.visible_to_client)

    def test_la_nota_tiene_que_ser_del_asunto_de_la_url(self):
        other = make_case(identification='1017000111')
        url = reverse(
            'case_manager:gestor_case_note_visibility',
            args=[other.pk, self.note.pk],
        )

        response = self.client.post(url, {'visible': '0'}, **FETCH)

        self.assertEqual(response.status_code, 404)
        self.note.refresh_from_db()
        self.assertTrue(self.note.visible_to_client)

    def test_la_ficha_pinta_el_interruptor_con_su_estado(self):
        page = reverse('case_manager:gestor_case_update', args=[self.case.pk])
        html = self.client.get(page).content.decode()

        self.assertIn('data-note-visible="true"', html)
        self.assertIn(self.url, html)
        self.assertIn('role="switch"', html)
        self.assertIn('data-unsaved-skip', html)
        self.assertIn('csrfmiddlewaretoken', html)

        self.client.post(self.url, {'visible': '0'}, **FETCH)
        html = self.client.get(page).content.decode()
        self.assertIn('data-note-visible="false"', html)

    def test_exporta_el_html_para_la_prueba_dom(self):
        """Con CASE_FLOW_HTML_DIR, deja `notes.html` para `gestor_ui.cjs`."""
        directory = os.environ.get('CASE_FLOW_HTML_DIR')
        if not directory:
            self.skipTest('CASE_FLOW_HTML_DIR no definido')
        response = self.client.get(
            reverse('case_manager:gestor_case_update', args=[self.case.pk])
        )
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        (path / 'notes.html').write_bytes(response.content)
        (path / 'notes_url.txt').write_text(self.url, encoding='utf-8')

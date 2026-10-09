"""Purga explícita, límites, dependencias, disco y auditoría mínima."""
from datetime import datetime, time, timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from auditlog.models import LogEntry
from django.contrib import admin
from django.core.files.base import ContentFile
from django.core.management import call_command, CommandError
from django.db import transaction
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone

from ..choices import Service
from ..models import CaseFinanceModel, CaseModel, CaseNoteModel, ClientModel, PazYSalvoDocumentModel
from .test_access import make_user, login_as


@override_settings(SOFT_DELETE_RETENTION_DAYS=90)
class PurgeDeletedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = make_user('purger_private_name', gestor=True, staff=True)

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.limit = timezone.make_aware(datetime.combine(
            timezone.localdate() - timedelta(days=90), time.min))
        self.old = self.limit - timedelta(days=1)
        self.person = ClientModel.objects.create(identification='88776655', full_name='Persona Privada')
        self.case = CaseModel.objects.create(client=self.person, service=Service.JUDICIAL,
                                             case_number='RADICADO-SECRETO')
        self.case.soft_delete(self.actor, at=self.old)

    def run_command(self, *args):
        output = StringIO()
        call_command('purge_deleted', *args, stdout=output)
        return output.getvalue()

    def document(self, **kwargs):
        defaults = dict(case=self.case, authorized_at=self.old, idempotency_key='purge-test')
        defaults.update(kwargs)
        return PazYSalvoDocumentModel.objects.create(**defaults)

    def test_simulation_lists_candidates_and_changes_nothing(self):
        finance = CaseFinanceModel._base_manager.create(case=self.case)
        document = self.document()
        output = self.run_command()
        for expected in [str(self.case.pk)[:8], self.person.full_name, 'RADICADO-SECRETO',
                         self.case.service_display, self.old.isoformat(), str(self.actor.pk)[:8],
                         'asuntos=1, clientes=0, registros=1', 'SIMULACIÓN']:
            self.assertIn(expected, output)
        self.assertTrue(CaseModel.all_objects.filter(pk=self.case.pk).exists())
        self.assertTrue(CaseFinanceModel._base_manager.filter(pk=finance.pk).exists())
        self.assertTrue(PazYSalvoDocumentModel.objects.filter(pk=document.pk).exists())

    def test_apply_confirmation_purges_dependencies_files_and_logs_no_pii(self):
        finance = CaseFinanceModel._base_manager.create(case=self.case)
        note = CaseNoteModel._base_manager.create(case=self.case, title='Nota privada', body='Secreto')
        doc = self.document(status='REVOKED', gea_document_id='gea-private', gea_revoked=True,
                            certified_at=self.old)
        doc.source_file.save('source.pdf', ContentFile(b'original'))
        doc.public_copy_file.save('public.pdf', ContentFile(b'copy'))
        paths = [Path(doc.source_file.path), Path(doc.public_copy_file.path)]
        self.person.soft_delete(self.actor, at=self.old)
        audit_count = LogEntry.objects.count()
        with patch('builtins.input', return_value='2') as confirmation, \
                self.assertLogs('case_manager.purge', level='INFO') as logs, \
                self.captureOnCommitCallbacks(execute=True):
            self.run_command('--apply')
        confirmation.assert_called_once()
        self.assertFalse(CaseModel.all_objects.filter(pk=self.case.pk).exists())
        self.assertFalse(ClientModel.all_objects.filter(pk=self.person.pk).exists())
        self.assertFalse(CaseFinanceModel._base_manager.filter(pk=finance.pk).exists())
        self.assertFalse(CaseNoteModel._base_manager.filter(pk=note.pk).exists())
        self.assertFalse(PazYSalvoDocumentModel.objects.filter(pk=doc.pk).exists())
        self.assertTrue(all(not path.exists() for path in paths))
        self.assertEqual(LogEntry.objects.count(), audit_count)
        self.assertEqual(len(logs.output), 2)
        text = '\n'.join(logs.output)
        for secret in [self.person.full_name, self.person.identification, self.actor.username,
                       self.actor.email, 'RADICADO-SECRETO', 'Nota privada', 'gea-private']:
            self.assertNotIn(secret, text)
        for expected in [str(self.case.pk)[:8], str(self.person.pk)[:8],
                         str(self.actor.pk)[:8], self.old.isoformat(), 'fecha=']:
            self.assertIn(expected, text)

    def test_wrong_confirmation_and_eof_do_not_delete(self):
        for answer in ['0', 'yes', '01', '1 ']:
            with patch('builtins.input', return_value=answer), self.assertRaises(CommandError):
                self.run_command('--apply')
            self.assertTrue(CaseModel.all_objects.filter(pk=self.case.pk).exists())
        with patch('builtins.input', side_effect=EOFError), self.assertRaises(CommandError):
            self.run_command('--apply')

    def test_yes_requires_apply(self):
        with self.assertRaises(CommandError):
            self.run_command('--yes')
        self.assertTrue(CaseModel.all_objects.filter(pk=self.case.pk).exists())

    def test_active_recent_and_exact_cutoff_are_untouched(self):
        protected = []
        for deleted_at in [None, timezone.now(), self.limit]:
            obj = CaseModel.objects.create(client=self.person, service=Service.JUDICIAL)
            if deleted_at:
                obj.soft_delete(self.actor, at=deleted_at)
            protected.append(obj.pk)
        with self.captureOnCommitCallbacks(execute=True), patch('builtins.input') as confirm:
            self.run_command('--apply', '--yes')
        confirm.assert_not_called()
        self.assertEqual(set(CaseModel.all_objects.values_list('pk', flat=True)), set(protected))
        self.assertTrue(ClientModel.objects.filter(pk=self.person.pk).exists())

    def test_client_with_nonexpired_or_live_case_is_blocked(self):
        self.person.soft_delete(self.actor, at=self.old)
        other = CaseModel.all_objects.create(client=self.person, service=Service.JUDICIAL)
        for deleted_at in [None, timezone.now()]:
            CaseModel.all_objects.filter(pk=other.pk).update(deleted_at=deleted_at)
            output = self.run_command()
            self.assertIn('BLOQUEADO', output)
            self.assertIn('activo o no vencido', output)
            self.assertIn('asuntos=1, clientes=0', output)
        with self.captureOnCommitCallbacks(execute=True):
            self.run_command('--apply', '--yes')
        self.assertTrue(ClientModel.all_objects.filter(pk=self.person.pk).exists())
        self.assertTrue(CaseModel.all_objects.filter(pk=other.pk).exists())

    def test_certified_and_locally_revoked_documents_block_case_and_client(self):
        self.person.soft_delete(self.actor, at=self.old)
        doc = self.document(status='CERTIFIED', certified_at=self.old, gea_document_id='gea-id')
        for status in ['CERTIFIED', 'REVOKED', 'FAILED']:
            doc.status = status
            doc.save()
            output = self.run_command('--apply', '--yes')
            self.assertIn('certificado sin revocar en gea', output)
            self.assertIn('asuntos=0, clientes=0', output)
            self.assertTrue(CaseModel.all_objects.filter(pk=self.case.pk).exists())
        doc.gea_revoked = True
        doc.status = 'REVOKED'
        doc.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.run_command('--apply', '--yes')
        self.assertFalse(ClientModel.all_objects.filter(pk=self.person.pk).exists())

    def test_before_must_be_strictly_older_and_correctly_formatted(self):
        for value in [timezone.localdate().isoformat(), self.limit.date().isoformat(),
                      '2026-99-99', '20260101']:
            with self.assertRaises(CommandError):
                self.run_command('--before', value, '--apply', '--yes')
        output = self.run_command('--before', (self.old - timedelta(days=1)).date().isoformat())
        self.assertIn('registros=0', output)
        self.assertTrue(CaseModel.all_objects.filter(pk=self.case.pk).exists())

    @override_settings(SOFT_DELETE_RETENTION_DAYS=120)
    def test_configured_retention(self):
        self.assertIn('registros=0', self.run_command())
        self.assertEqual(self.case.purge_after, self.old + timedelta(days=120))

    def test_restored_during_confirmation_is_not_purged(self):
        def confirm(prompt):
            self.case.restore()
            return '1'
        with patch('builtins.input', side_effect=confirm):
            output = self.run_command('--apply')
        self.assertIn('Omitido asunto', output)
        self.assertTrue(CaseModel.objects.filter(pk=self.case.pk).exists())

    def test_rollback_preserves_files_and_does_not_log(self):
        doc = self.document()
        doc.source_file.save('source.pdf', ContentFile(b'original'))
        with self.assertNoLogs('case_manager.purge'), self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self.run_command('--apply', '--yes')
                    raise RuntimeError('rollback')
            except RuntimeError:
                pass
        self.assertTrue(Path(doc.source_file.path).exists())
        self.assertTrue(CaseModel.all_objects.filter(pk=self.case.pk).exists())

    def test_admin_and_gestor_show_readonly_retention_dates(self):
        self.person.soft_delete(self.actor, at=self.old)
        login_as(self.client, self.actor.username)
        expected = timezone.localtime(self.old + timedelta(days=90)).strftime('%Y-%m-%d')
        for model, obj, view in [(CaseModel, self.case, 'gestor_case_list'),
                                 (ClientModel, self.person, 'gestor_client_list')]:
            model_admin = admin.site._registry[model]
            request = RequestFactory().get('/', {'deleted': 'yes'})
            self.assertIn('purge_date', model_admin.get_list_display(request))
            self.assertEqual(model_admin.purge_date(obj), expected)
            response = self.client.get(reverse('case_manager:' + view), {'deleted': 'yes'})
            self.assertContains(response, expected)
            self.assertContains(response, 'Se elimina definitivamente el')
            self.assertNotContains(response, 'data-delete-url')

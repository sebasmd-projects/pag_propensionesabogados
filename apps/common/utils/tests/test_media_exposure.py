# apps/common/utils/tests/test_media_exposure.py
"""
Que ninguna carpeta de subidas la reparta el servidor web por su cuenta.

El servidor web sirve `MEDIA_URL` **sin pasar por Django**: un fichero que
Apache entrega antes de que Django lo vea no pasa por ningun control, por
muchas comprobaciones que tenga la vista. Lo sensible de pag --los PDF del
paz y salvo, que llevan cedula y nombre-- vive por eso **fuera** de
`MEDIA_ROOT`, en `PRIVATE_MEDIA_ROOT`, con un almacen que ni siquiera sabe
construir una URL.

Aqui se comprueban las dos mitades: que lo privado sigue fuera, y que un campo
de fichero nuevo bajo `MEDIA_ROOT` no se puede colar sin decidir si es publico
(y escribir por que) o moverlo a lo privado.

    manage.py test apps.common.utils.tests.test_media_exposure \\
        --settings=app_core.settings_test
"""

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.db import models
from django.test import TestCase, override_settings
from django.utils import timezone

from .. import media_audit
from ..management.commands.check_security import Command
from ..media_audit import (PUBLICLY_SERVABLE_MEDIA, private_fields,
                           upload_fields, upload_prefixes)

#: Lo que guarda datos personales y por tanto no puede servirse directo.
MUST_BE_PRIVATE = ('paz_y_salvo',)


def check_security_section():
    out = StringIO()
    call_command('check_security', stdout=out)

    return out.getvalue().split('5. Carpetas')[1].split('6. Ajustes')[0]


class ThePrivateFilesStayPrivateTests(TestCase):

    def test_the_paz_y_salvo_pdfs_are_outside_media_root(self):
        labels = {row['label'] for row in private_fields()}

        self.assertEqual(labels, {
            'case_manager.PazYSalvoDocumentModel.source_file',
            'case_manager.PazYSalvoDocumentModel.public_copy_file',
        })

    def test_no_sensitive_folder_is_declared_publicly_servable(self):
        for folder in MUST_BE_PRIVATE:
            with self.subTest(folder=folder):
                self.assertNotIn(folder, PUBLICLY_SERVABLE_MEDIA)
                self.assertNotIn(folder, upload_prefixes())

    def test_the_private_storage_cannot_build_a_url(self):
        """Un almacen sin URL no puede acabar enlazado por `MEDIA_URL`."""
        row = private_fields()[0]

        with self.assertRaises(ValueError):
            row['field'].storage.url('x.pdf')

    def test_the_private_root_follows_the_setting(self):
        """La ubicacion se lee en cada uso, no al importar."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as folder:
            with override_settings(PRIVATE_MEDIA_ROOT=folder):
                row = private_fields()[0]

                self.assertEqual(row['root'], Path(folder).resolve())


class WhatSitsUnderMediaRootIsDeclaredTests(TestCase):
    """
    Lo que cuelga de `MEDIA_ROOT` es publico: tiene que haber una razon
    escrita por cada carpeta.
    """

    def test_every_folder_under_media_root_is_declared_with_a_reason(self):
        for prefix in upload_prefixes():
            with self.subTest(prefix=prefix):
                self.assertIn(prefix, PUBLICLY_SERVABLE_MEDIA)
                self.assertGreater(len(PUBLICLY_SERVABLE_MEDIA[prefix]), 20)

    def test_the_declared_folders_are_the_site_content_ones(self):
        self.assertEqual(
            set(upload_prefixes()), {'team', 'modal_banners'})

    def test_every_declared_folder_still_has_a_field(self):
        """Una entrada sin campo ya no declara nada: sobra."""
        self.assertEqual(
            set(PUBLICLY_SERVABLE_MEDIA) - set(upload_prefixes()), set())


class TheCheckReadsTheRealPathsTests(TestCase):
    """
    Que el comando lea bien a donde escribe cada campo.

    Esta parte ya fallo dos veces mientras se escribia en gea, y las dos en
    silencio, que es lo que la hace peligrosa: una comprobacion que no sabe
    leer un campo lo da por bueno. Primero una expresion regular leia tambien
    el docstring; luego un `ast.walk` --que recorre en anchura, no en orden de
    codigo-- devolvia el valor por defecto de un nombre y no la carpeta. Hoy se
    mira lo que se **devuelve**.
    """

    def test_every_upload_field_resolves_to_a_folder(self):
        for row in upload_fields():
            self.assertNotEqual(
                row['prefix'], media_audit.UNKNOWN_PREFIX, row['label'])

    def test_it_reads_a_function_upload_to_that_returns_an_f_string(self):
        """`paz_y_salvo_source_path` devuelve `f'paz_y_salvo/{...}'`."""
        prefixes = {row['label']: row['prefix'] for row in upload_fields()}

        self.assertEqual(
            prefixes['case_manager.PazYSalvoDocumentModel.source_file'],
            'paz_y_salvo')

    def test_it_reads_a_plain_string_upload_to(self):
        prefixes = {row['label']: row['prefix'] for row in upload_fields()}

        self.assertEqual(prefixes['core.TeamMemberModel.photo'], 'team')

    def test_it_reads_the_returned_path_and_not_a_default_value(self):
        def upload_path(instance, filename):
            name = getattr(instance, 'name', None) or 'default'
            return f'ventas/{name}/{filename}'

        self.assertEqual(media_audit.prefix_from_function(upload_path), 'ventas')

    def test_it_resolves_a_path_returned_by_name(self):
        """`path = os.path.join(...)` y luego `return path`."""
        import os

        def upload_path(instance, filename):
            path = os.path.join('archivo', filename)
            return path

        self.assertEqual(media_audit.prefix_from_function(upload_path), 'archivo')

    def test_a_function_it_cannot_read_is_reported_not_skipped(self):
        upload_to = lambda instance, filename: filename  # noqa: E731

        # `None` es lo que `upload_fields()` convierte en `UNKNOWN_PREFIX`, y
        # eso es un hallazgo en `check_security`, no un campo que se salta.
        self.assertIsNone(media_audit.prefix_from_function(upload_to))


class TheCheckCatchesANewFieldTests(TestCase):
    """El objetivo de todo esto: un campo nuevo no se cuela en silencio."""

    def fake_field(self, label, prefix, private=False):
        model = mock.Mock()
        model._meta.label = label.rsplit('.', 1)[0]

        return {
            'label': label, 'model': model,
            'field': models.FileField(upload_to=prefix),
            'prefix': prefix, 'root': None, 'private': private,
        }

    def test_the_repo_as_it_is_reports_nothing_in_the_uploads_section(self):
        self.assertNotIn('AVISO', check_security_section())

    def test_an_undeclared_folder_under_media_root_is_reported(self):
        row = self.fake_field('pqrs.PQRSModel.cedula', 'cedulas')

        with mock.patch.object(Command, '_upload_prefixes',
                               return_value={'cedulas': [row['label']]}):
            section = check_security_section()

        self.assertIn('AVISO', section)
        self.assertIn('cedulas', section)
        self.assertIn('PUBLICLY_SERVABLE_MEDIA', section)

    def test_a_field_it_cannot_read_is_reported(self):
        with mock.patch.object(
                Command, '_upload_prefixes',
                return_value={media_audit.UNKNOWN_PREFIX: ['x.Y.z']}):
            section = check_security_section()

        self.assertIn('No se pudo leer', section)

    def test_a_private_root_inside_public_html_is_reported(self):
        with override_settings(
                PRIVATE_MEDIA_ROOT='/home/propensi/public_html/privado'):
            section = check_security_section()

        self.assertIn('public_html', section)

    def test_a_private_root_that_contains_media_root_is_reported(self):
        with override_settings(
                MEDIA_ROOT='/srv/app/private/media',
                PRIVATE_MEDIA_ROOT='/srv/app/private'):
            section = check_security_section()

        self.assertIn('contiene', section)

    def test_ckeditor_accepting_any_file_type_is_reported(self):
        with override_settings(CKEDITOR_5_ALLOW_ALL_FILE_TYPES=True):
            section = check_security_section()

        self.assertIn('CKEDITOR_5_ALLOW_ALL_FILE_TYPES', section)


class CheckMediaTests(TestCase):

    def test_it_runs_and_names_both_roots(self):
        out = StringIO()

        with override_settings(
                MEDIA_ROOT='/no/existe/media',
                PRIVATE_MEDIA_ROOT='/no/existe/privado'):
            call_command('check_media', stdout=out)

        text = out.getvalue()

        self.assertIn('MEDIA_ROOT (publico)', text)
        self.assertIn('PRIVATE_MEDIA_ROOT', text)
        self.assertIn('team/ se sirve directo', text)

    def test_a_private_root_inside_media_root_is_a_problem(self):
        out = StringIO()

        with override_settings(
                MEDIA_ROOT='/srv/media',
                PRIVATE_MEDIA_ROOT='/srv/media/privado'):
            call_command('check_media', stdout=out)

        self.assertIn('dentro de MEDIA_ROOT', out.getvalue())

    def test_a_missing_file_is_named(self):
        from apps.project.api.platform.case_manager.models import (
            CaseModel, ClientModel, PazYSalvoDocumentModel)

        client = ClientModel.objects.create(
            identification='77', full_name='Cliente', email='c@example.test')
        case = CaseModel.objects.create(client=client)
        PazYSalvoDocumentModel.objects.create(
            case=case, authorized_at=timezone.now(), source_file='paz_y_salvo/x/no-esta-source.pdf')

        out = StringIO()
        call_command('check_media', stdout=out)

        self.assertIn('NO estan en disco', out.getvalue())
        self.assertIn('no-esta-source.pdf', out.getvalue())

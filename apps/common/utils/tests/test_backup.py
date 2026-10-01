# apps/common/utils/tests/test_backup.py
"""
Que un respaldo no sea la PII descifrada esperando a que alguien la copie.

`dumpdata` serializa el **valor de Python** de cada campo, y en los de
``django-encrypted-model-fields`` ese valor es el ya descifrado. Asi que los
respaldos de la plataforma salian con la cedula y la fecha de nacimiento de
cada cliente en claro: el respaldo deshacia el cifrado de campo.
`FIELD_ENCRYPTION_KEY` protege la base de datos contra un volcado robado, y el
volcado de al lado sin llave era ese volcado robado ya servido.

La primera prueba de la clase de abajo es la que **reproduce el fallo**:
comprueba que `dumpdata` en crudo saca la cedula legible. Si algun dia la
biblioteca cambia y deja de hacerlo, esa prueba falla y avisa de que la razon
de ser de todo esto ya no existe -- que es informacion util, no una molestia.

    manage.py test apps.common.utils.tests.test_backup \\
        --settings=app_core.settings_test
"""

import os
import stat
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase

from apps.common.core.models import ContactModel
from apps.project.api.platform.auth_platform.models import \
    AttlasInsolvencyAuthModel
from apps.project.case_manager.models import (CaseModel,
                                                           ClientModel)
from apps.project.api.platform.insolvency_form.models import (
    AttlasInsolvencyFormModel, AttlasInsolvencySignatureModel)
from apps.project.api.pqrs.models import PQRSModel
from apps.project.common.users.models import UserModel

from ..backup_crypto import (LEGACY_PASSPHRASE_ENV, PASSPHRASE_ENV,
                             BackupCryptoError, decrypt, encrypt,
                             passphrase_from)
from ..management.commands import db_backup
from ..testing import posix_only

PASSPHRASE = 'una-contrasena-de-respaldo-larga'
SECRET_EMAIL = 'secreto@example.com'
SECRET_DOCUMENT = '90817263540'
SECRET_CLIENT_EMAIL = 'cliente-secreto@example.test'
SECRET_CONTACT_EMAIL = 'contacto-secreto@example.test'
SECRET_PQRS_EMAIL = 'pqrs-secreto@example.test'
SECRET_DEBTOR_EMAIL = 'deudor-secreto@example.test'
SECRET_SIGNATURE = 'data:image/png;base64,FIRMA-SECRETA-123'
SECRET_IP = '203.0.113.77'

#: Todo lo que tiene que quedar dentro del volcado con datos personales, y
#: por tanto fuera del general.
ALL_SECRETS = (
    SECRET_EMAIL, SECRET_DOCUMENT, SECRET_CLIENT_EMAIL, SECRET_CONTACT_EMAIL,
    SECRET_PQRS_EMAIL, SECRET_DEBTOR_EMAIL, SECRET_SIGNATURE, SECRET_IP,
)


def make_pii():
    """Una fila con datos personales en cada app que el respaldo cubre."""
    UserModel.objects.create_user(
        username='ana', email=SECRET_EMAIL, password='pw-for-tests-123',
        first_name='Ana', last_name='Perez',
    )

    auth = AttlasInsolvencyAuthModel.objects.create(
        document_number=SECRET_DOCUMENT, birth_date=date(1990, 2, 3),
    )

    form = AttlasInsolvencyFormModel.objects.create(
        user=auth, debtor_first_name='Ana', debtor_last_name='Perez',
        debtor_email=SECRET_DEBTOR_EMAIL, debtor_cell_phone='3001234567',
        debtor_address='Calle 10', debtor_birth_date=date(1990, 2, 3),
    )
    AttlasInsolvencySignatureModel.objects.create(
        form=form, signature=SECRET_SIGNATURE)

    client = ClientModel.objects.create(
        identification='1001', full_name='Cliente Secreto',
        email=SECRET_CLIENT_EMAIL,
    )
    CaseModel.objects.create(client=client)

    ContactModel.objects.create(
        name='Luz', last_name='Mora', email=SECRET_CONTACT_EMAIL,
        subject='hola', message='mensaje',
    )

    PQRSModel.objects.create(
        name='Luz', surname='Mora', email=SECRET_PQRS_EMAIL,
        id_number='55', description='queja',
    )

    from ..models import IPBlockedModel

    IPBlockedModel.objects.create(current_ip=SECRET_IP)


class TheProblemThisSolvesTests(TestCase):
    """La razon de ser, escrita como prueba para que no se olvide."""

    def test_dumpdata_writes_the_pii_in_the_clear(self):
        AttlasInsolvencyAuthModel.objects.create(
            document_number=SECRET_DOCUMENT, birth_date=date(1990, 2, 3),
        )

        out = StringIO()
        call_command(
            'dumpdata', 'auth_platform.AttlasInsolvencyAuthModel', stdout=out)

        self.assertIn(
            SECRET_DOCUMENT, out.getvalue(),
            'si esto deja de cumplirse, el cifrado del respaldo sobra',
        )


class TheEnvelopeTests(SimpleTestCase):

    def test_it_comes_back_the_same(self):
        blob = encrypt(b'{"hola": "mundo"}', PASSPHRASE)

        self.assertEqual(decrypt(blob, PASSPHRASE), b'{"hola": "mundo"}')

    def test_the_content_is_not_readable(self):
        blob = encrypt(b'{"email": "secreto@example.com"}', PASSPHRASE)

        self.assertNotIn(b'secreto@example.com', blob)

    def test_the_wrong_passphrase_does_not_open_it(self):
        blob = encrypt(b'x', PASSPHRASE)

        with self.assertRaises(BackupCryptoError):
            decrypt(blob, 'otra-cosa')

    def test_a_tampered_file_is_refused_instead_of_returning_garbage(self):
        """
        Fernet esta autenticado, y eso importa: descifrar mal no puede
        devolver algo que parezca un JSON valido.
        """
        blob = bytearray(encrypt(b'{"a": 1}', PASSPHRASE))
        blob[-5] = blob[-5] ^ 0xFF

        with self.assertRaises(BackupCryptoError):
            decrypt(bytes(blob), PASSPHRASE)

    def test_two_backups_of_the_same_thing_look_different(self):
        """Sal distinta cada vez: si no, se ve que dos respaldos son iguales."""
        first = encrypt(b'{"a": 1}', PASSPHRASE)
        second = encrypt(b'{"a": 1}', PASSPHRASE)

        self.assertNotEqual(first, second)

    def test_something_that_is_not_a_backup_says_so(self):
        with self.assertRaises(BackupCryptoError):
            decrypt(b'esto no es un respaldo', PASSPHRASE)

    def test_the_header_says_what_it_is(self):
        """
        Quien se encuentre el fichero dentro de tres anos tiene que poder
        saber que es con un `head`, sin leer el codigo.
        """
        blob = encrypt(b'x', PASSPHRASE)

        self.assertTrue(blob.startswith(b'GEABACKUP1\n'))
        self.assertIn(b'scrypt n=', blob)


class ThePassphraseNameTests(SimpleTestCase):
    """``BACKUP_PASSPHRASE`` manda; la de gea solo se lee si falta."""

    def read(self, **env):
        with mock.patch.dict(os.environ, env, clear=False):
            for name in (PASSPHRASE_ENV, LEGACY_PASSPHRASE_ENV):
                if name not in env:
                    os.environ.pop(name, None)

            return passphrase_from()

    def test_the_pag_name_is_the_one(self):
        self.assertEqual(PASSPHRASE_ENV, 'BACKUP_PASSPHRASE')
        self.assertEqual(self.read(BACKUP_PASSPHRASE='nueva'), 'nueva')

    def test_the_gea_name_still_works_when_the_new_one_is_missing(self):
        self.assertEqual(self.read(GEA_BACKUP_PASSPHRASE='de-gea'), 'de-gea')

    def test_the_pag_name_wins_when_both_are_set(self):
        self.assertEqual(
            self.read(BACKUP_PASSPHRASE='nueva', GEA_BACKUP_PASSPHRASE='vieja'),
            'nueva',
        )

    def test_nothing_set_means_no_passphrase(self):
        self.assertEqual(self.read(), '')


class BackupTestCase(TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)

        make_pii()

    def with_passphrase(self, value=PASSPHRASE):
        """La frase puesta (o quitada) solo durante esta prueba."""
        patcher = mock.patch.dict(os.environ, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

        os.environ.pop(PASSPHRASE_ENV, None)
        os.environ.pop(LEGACY_PASSPHRASE_ENV, None)

        if value:
            os.environ[PASSPHRASE_ENV] = value

    def run_backup(self, **options):
        out = StringIO()
        call_command('db_backup', '-o', str(self.path), stdout=out,
                     stderr=out, **options)
        return out.getvalue()

    def written(self):
        return sorted(item.name for item in self.path.iterdir())


class TheBackupCommandTests(BackupTestCase):

    # -- con contraseña -------------------------------------------------
    def test_with_a_passphrase_the_pii_dump_is_encrypted(self):
        self.with_passphrase()

        self.run_backup()

        self.assertIn('pii_backup.json.enc', self.written())
        self.assertIn('h_pii_backup.json.enc', self.written())
        self.assertNotIn('pii_backup.json', self.written())
        self.assertNotIn('h_pii_backup.json', self.written())

    def test_the_encrypted_dump_does_not_leak_anything(self):
        self.with_passphrase()

        self.run_backup()

        for name in ('pii_backup.json.enc', 'h_pii_backup.json.enc'):
            blob = (self.path / name).read_bytes()

            for secret in ALL_SECRETS:
                self.assertNotIn(secret.encode(), blob, (name, secret))

    def test_it_can_be_opened_again(self):
        self.with_passphrase()

        self.run_backup()
        call_command(
            'db_restore_open', str(self.path / 'pii_backup.json.enc'),
            stdout=StringIO(),
        )

        recovered = (self.path / 'pii_backup.json').read_text(encoding='utf-8')

        for secret in ALL_SECRETS:
            self.assertIn(secret, recovered)

    def test_the_gea_passphrase_name_also_encrypts(self):
        """Compatibilidad: quien ya tiene `GEA_BACKUP_PASSPHRASE` puesta."""
        self.with_passphrase(None)
        os.environ[LEGACY_PASSPHRASE_ENV] = PASSPHRASE

        self.run_backup()

        self.assertIn('pii_backup.json.enc', self.written())

    def test_the_passphrase_can_come_from_a_file(self):
        self.with_passphrase(None)
        source = self.path / 'frase.txt'
        source.write_text(PASSPHRASE + '\n', encoding='utf-8')

        self.run_backup(passphrase_file=str(source))

        self.assertIn('pii_backup.json.enc', self.written())

    def test_opening_with_the_wrong_passphrase_fails(self):
        self.with_passphrase()
        self.run_backup()

        self.with_passphrase('otra-frase-distinta')

        with self.assertRaises(CommandError):
            call_command(
                'db_restore_open', str(self.path / 'pii_backup.json.enc'),
                stdout=StringIO(),
            )

    def test_opening_without_a_passphrase_fails(self):
        self.with_passphrase()
        self.run_backup()

        self.with_passphrase(None)

        with self.assertRaises(CommandError):
            call_command(
                'db_restore_open', str(self.path / 'pii_backup.json.enc'),
                stdout=StringIO(),
            )

    # -- sin contraseña -------------------------------------------------
    def test_without_a_passphrase_the_pii_is_simply_not_written(self):
        """
        El defecto seguro. Antes se escribia igual, en claro y legible por
        cualquiera de la maquina.
        """
        self.with_passphrase(None)

        output = self.run_backup()

        self.assertNotIn('pii_backup.json', self.written())
        self.assertNotIn('h_pii_backup.json', self.written())
        self.assertIn('backup.json', self.written())
        self.assertIn(PASSPHRASE_ENV, output)

        for name in self.written():
            text = (self.path / name).read_text(encoding='utf-8')

            for secret in ALL_SECRETS:
                self.assertNotIn(secret, text, (name, secret))

    def test_writing_it_in_the_clear_has_to_be_asked_for(self):
        self.with_passphrase(None)

        self.run_backup(allow_plaintext=True)

        self.assertIn('pii_backup.json', self.written())

    # -- permisos -------------------------------------------------------
    @posix_only
    def test_everything_is_written_readable_only_by_its_owner(self):
        """
        El caso mas tonto y mas frecuente: el respaldo en un directorio que
        comparte la cuenta de hosting.

        Solo en POSIX. Windows no tiene el modo `rw-------` de Unix --`os.open`
        con 0o600 alli solo controla el bit de solo lectura-- asi que esta
        asercion fallaria en un portatil sin que nada estuviera roto. La
        propiedad importa en el servidor, que es Linux; por eso se salta en vez
        de borrarse.
        """
        self.with_passphrase()

        self.run_backup()

        for item in self.path.iterdir():
            mode = stat.S_IMODE(item.stat().st_mode)

            self.assertEqual(
                mode, 0o600, f'{item.name} salio con permisos {oct(mode)}')

    def test_the_files_are_written_on_any_system(self):
        """
        Lo que la de arriba no puede comprobar en Windows: que el respaldo se
        escriba, y **intacto** --en Windows `os.open` abre en modo texto y
        traduciria los saltos de linea del fichero cifrado--. Los permisos son
        una propiedad de POSIX; existir y abrirse, no.
        """
        self.with_passphrase()

        self.run_backup()

        for name in ('backup.json', 'h_backup.json', 'pii_backup.json.enc',
                     'h_pii_backup.json.enc'):
            self.assertIn(name, self.written())
            self.assertGreater((self.path / name).stat().st_size, 0)

        blob = (self.path / 'pii_backup.json.enc').read_bytes()

        self.assertNotIn(b'\r\n', blob.split(b'\n', 1)[1])
        self.assertEqual(decrypt(blob, PASSPHRASE)[:1], b'[')


class TheGeneralDumpTests(BackupTestCase):

    def test_the_general_dump_carries_no_pii(self):
        self.with_passphrase()

        self.run_backup()

        for name in ('backup.json', 'h_backup.json'):
            general = (self.path / name).read_text(encoding='utf-8')

            for secret in ALL_SECRETS:
                self.assertNotIn(secret, general, (name, secret))

    def test_the_contact_form_is_not_in_the_general_dump(self):
        """`core` es una app general, pero `ContactModel` lleva correos."""
        self.with_passphrase()

        self.run_backup()

        general = (self.path / 'backup.json').read_text(encoding='utf-8')

        self.assertNotIn('core.contactmodel', general)

    def test_adding_a_pii_app_to_the_general_dump_is_refused(self):
        """
        Hoy se cumple, y sin esta comprobacion se cumpliria hasta que alguien
        anadiera una app sin caer en que sus modelos llevan datos personales.
        El fallo saldria en un fichero, meses despues.
        """
        with mock.patch.object(
                db_backup, 'GENERAL_APPS', db_backup.GENERAL_APPS + ['users']):
            with self.assertRaises(CommandError):
                self.run_backup()

    def test_a_model_with_encrypted_fields_in_a_general_app_is_refused(self):
        """
        La red de seguridad automatica: aunque la lista de apps con PII se
        quede corta, un campo cifrado en el volcado general no pasa.
        """
        with mock.patch.object(
                db_backup, 'GENERAL_APPS',
                db_backup.GENERAL_APPS + ['auth_platform']), \
                mock.patch.object(db_backup, 'APPS_WITH_PII', set()):
            with self.assertRaises(CommandError) as raised:
                self.run_backup()

        self.assertIn('campos cifrados', str(raised.exception))


class TheCoverageTests(BackupTestCase):
    """Lo que el respaldo cubre, dicho en una prueba."""

    def dumped_models(self):
        self.with_passphrase()
        self.run_backup()
        call_command(
            'db_restore_open', str(self.path / 'pii_backup.json.enc'),
            stdout=StringIO(),
        )

        import json

        rows = json.loads(
            (self.path / 'pii_backup.json').read_text(encoding='utf-8'))

        return {row['model'] for row in rows}

    def test_every_pii_app_of_the_project_is_covered(self):
        models = self.dumped_models()

        for expected in (
            'users.usermodel',
            'auth_platform.attlasinsolvencyauthmodel',
            'insolvency_form.attlasinsolvencyformmodel',
            'insolvency_form.attlasinsolvencysignaturemodel',
            'case_manager.clientmodel',
            'case_manager.casemodel',
            'pqrs.pqrsmodel',
            'core.contactmodel',
            'utils.ipblockedmodel',
        ):
            self.assertIn(expected, models)

    def test_every_declared_target_exists(self):
        """Un nombre mal escrito en la lista se quedaria sin volcar en silencio."""
        from django.apps import apps

        for label in db_backup.APPS_WITH_PII | set(db_backup.GENERAL_APPS):
            apps.get_app_config(label)

        for label in db_backup.MODELS_WITH_PII:
            apps.get_model(label)

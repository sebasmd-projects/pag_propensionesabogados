# apps/common/utils/management/commands/db_backup.py
"""
Respaldos de la base de datos, sin deshacer el cifrado de campo.

Lo que hacia y por que era un problema
--------------------------------------
``dumpdata`` serializa el **valor de Python** de cada campo, y en los campos de
``django-encrypted-model-fields`` ese valor es el ya descifrado. Aqui son la
cedula y la fecha de nacimiento de ``auth_platform.AttlasInsolvencyAuthModel``:
el volcado las sacaba **en claro**. El respaldo deshacia el cifrado de campo:
`FIELD_ENCRYPTION_KEY` protege la base de datos contra un volcado robado, y el
volcado de al lado, sin llave y con permisos de lectura para todo el mundo, era
ese volcado robado ya servido. Y un respaldo no se queda quieto: acaba en un
portatil, en un adjunto o en una carpeta compartida.

Tres cosas cambian
------------------
1. **El fichero se cifra** con una contrasena (``backup_crypto.py``), asi que
   descargarlo no basta para leerlo. Se abre con ``manage.py db_restore_open``.
   La contrasena es ``BACKUP_PASSPHRASE`` (o, si falta, la de gea,
   ``GEA_BACKUP_PASSPHRASE``), o un fichero con ``--passphrase-file``.
2. **Permisos 600** en todo lo que se escribe, cifrado o no. Es una linea y
   cubre el caso mas tonto y mas frecuente: el respaldo en un directorio que
   comparte la cuenta de hosting.
3. **Sin contrasena no se escribe PII en claro.** El volcado con datos
   personales se salta, con un aviso que dice como arreglarlo. Escribirlo
   igualmente exige pedirlo a mano con ``--allow-plaintext``, que es justo la
   friccion que hace falta para que sea una decision y no un descuido.

Que cubre y que no
------------------
Salen **dos** volcados, cada uno en version legible (``h_*``, con sangrado) y
compacta:

* ``backup.json`` -- **sin datos personales**: ``core`` (equipo, avisos
  modales; **sin** ``core.ContactModel``, que lleva nombre, correo y mensaje
  de quien escribe), ``faq``, ``financial_education`` y ``calculator``.
* ``pii_backup.json`` -- **con datos personales**, cifrado: ``users``
  (usuarios), ``account`` (intentos de acceso, atados al usuario),
  ``auth_platform`` (clientes de la plataforma y asesores), ``case_manager``
  (clientes, asuntos, finanzas, notas y paz y salvo del gestor),
  ``insolvency_form`` (formulario de insolvencia, con la firma en base64),
  ``pqrs``, ``core.ContactModel`` y ``utils`` (IP bloqueadas y de la lista
  blanca: una IP es un dato personal).

**No cubre**, y conviene saberlo: no es un respaldo completo de la
plataforma.

* ``auditlog.LogEntry``: el historial de cambios lleva instantaneas de los
  registros, con su PII dentro; es historial, no estado, y no se arrastra.
* ``axes`` (accesos y bloqueos), ``sessions`` y ``admin.LogEntry``.
* El **segundo factor** (``django_otp``, ``two_factor``): dispositivos TOTP y
  codigos de un solo uso. Tras restaurar, cada usuario tiene que volver a
  enrolar su segundo factor (o se copian esas tablas aparte, con cuidado: son
  secretos).
* ``auth.Group`` y ``auth.Permission``: el grupo del gestor se recrea con
  ``manage.py setup_case_manager_group`` **antes** de ``loaddata``, y hay que
  comprobar despues la pertenencia de cada usuario (``groups``).
* **Los ficheros**: ``MEDIA_ROOT`` (fotos del equipo, imagenes de CKEditor) y
  sobre todo ``PRIVATE_MEDIA_ROOT`` (los PDF del paz y salvo, original y
  copia) son ficheros de disco, no filas; hay que copiarlos aparte, y los
  PDF llevan datos personales, asi que cifrados tambien. La firma manuscrita
  del formulario **si** esta, porque vive en la base de datos.
* Esquema y migraciones: ``dumpdata`` guarda datos; el esquema lo crea
  ``migrate``.

El volcado general no lleva PII, y hay dos comprobaciones que lo sostienen: las
apps con datos personales estan declaradas abajo y, ademas, ningun modelo del
volcado general puede tener un campo cifrado. Si alguno acabara ahi, el
comando se niega en vez de escribirlo.
"""

import os
from io import StringIO
from pathlib import Path

from django.apps import apps as django_apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.common.utils.backup_crypto import (PASSPHRASE_ENV,
                                             BackupCryptoError, encrypt,
                                             passphrase_from)

#: Apps cuyos modelos llevan datos personales. Un volcado suyo es PII.
#:
#: La lista es explicita a proposito: una comprobacion automatica que recorriera
#: los modelos seria mas lista y tambien mas facil de romper en silencio. Solo
#: los campos cifrados se buscan automaticamente (`_refuse_pii_in_the_general_
#: dump`), como red de seguridad y no como criterio.
APPS_WITH_PII = {
    'users', 'account', 'auth_platform', 'case_manager', 'insolvency_form',
    'pqrs', 'utils',
}

#: Modelos con PII dentro de apps que, por lo demas, se pueden guardar sin
#: cifrar (`core`).
MODELS_WITH_PII = {'core.ContactModel'}

#: El volcado general: lo que se puede guardar sin PII dentro.
GENERAL_APPS = ['core', 'faq', 'financial_education', 'calculator']

#: El volcado con datos personales: las apps de arriba y los modelos sueltos.
PII_TARGETS = sorted(APPS_WITH_PII) + sorted(MODELS_WITH_PII)

#: Sistema y terceros que no interesa arrastrar.
EXCLUDE = [
    'contenttypes',
    'auth.Permission',
    'admin.LogEntry',
    'sessions.Session',
    'axes.AccessAttempt',
    'axes.AccessLog',
    'auditlog.LogEntry',
]

#: Lo que se saca del volcado general: lo de arriba y los modelos con PII de
#: las apps generales (`core`).
GENERAL_EXCLUDE = EXCLUDE + sorted(MODELS_WITH_PII)


class Command(BaseCommand):
    help = (
        'Genera respaldos JSON. Los que llevan datos personales se cifran con '
        'una contraseña; sin ella no se escriben.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-o', '--output-dir',
            default='.',
            help='Directorio de salida (por defecto: el actual).',
        )
        parser.add_argument(
            '--passphrase-file',
            help=(
                'Fichero con la contraseña de cifrado. Si no se indica se usa '
                f'la variable de entorno {PASSPHRASE_ENV}. No hay opción para '
                'pasarla como argumento: acabaría en el historial y en «ps».'
            ),
        )
        parser.add_argument(
            '--allow-plaintext',
            action='store_true',
            help=(
                'Escribe el volcado con datos personales SIN cifrar. Es PII '
                'en claro en un fichero; hay que pedirlo a mano y a sabiendas.'
            ),
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        self._refuse_pii_in_the_general_dump()

        passphrase = passphrase_from(options.get('passphrase_file'))

        files = [
            ('h_backup.json', GENERAL_APPS, GENERAL_EXCLUDE, 4, False),
            ('backup.json', GENERAL_APPS, GENERAL_EXCLUDE, None, False),
            ('h_pii_backup.json', PII_TARGETS, EXCLUDE, 4, True),
            ('pii_backup.json', PII_TARGETS, EXCLUDE, None, True),
        ]

        for filename, targets, exclude, indent, carries_pii in files:
            self._write(
                output_dir, filename, targets, exclude, indent, carries_pii,
                passphrase, options['allow_plaintext'],
            )

        if not passphrase:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'Los volcados con datos personales NO se han escrito: llevan '
                'cédulas, correos y teléfonos en claro y no había contraseña '
                'con la que cifrarlos.'
            ))
            self.stdout.write(
                f'   Pon {PASSPHRASE_ENV} en el entorno, o pasa '
                '--passphrase-file, y vuelve a lanzarlo.'
            )

    # ------------------------------------------------------------------
    def _refuse_pii_in_the_general_dump(self):
        """
        Que el volcado «sin datos personales» siga sin llevarlos.

        Hoy se cumple, y sin esta comprobación se cumpliría hasta que alguien
        añadiera una app a la lista de arriba sin caer en que sus modelos
        llevan datos personales. El fallo saldría en un fichero, meses
        después. Dos comprobaciones: que ninguna app general esté en la lista
        de PII, y que ningún modelo de las apps generales (menos los
        excluidos) tenga un campo cifrado.
        """
        offenders = APPS_WITH_PII.intersection(GENERAL_APPS)

        if offenders:
            raise CommandError(
                'GENERAL_APPS incluye apps con datos personales: '
                f'{", ".join(sorted(offenders))}. Ese volcado se escribe sin '
                'cifrar, así que o sale de la lista o pasa al de datos '
                'personales.'
            )

        excluded = set(GENERAL_EXCLUDE)
        encrypted = []

        for label in GENERAL_APPS:
            try:
                config = django_apps.get_app_config(label)
            except LookupError:
                raise CommandError(
                    f'GENERAL_APPS incluye «{label}», que no es una app '
                    'instalada.'
                )

            for model in config.get_models():
                if model._meta.label in excluded:
                    continue

                for field in model._meta.get_fields():
                    if field.__class__.__name__.startswith('Encrypted'):
                        encrypted.append(f'{model._meta.label}.{field.name}')

        if encrypted:
            raise CommandError(
                'El volcado general incluiría campos cifrados, o sea PII: '
                f'{", ".join(encrypted)}. Muévelos al volcado de datos '
                'personales.'
            )

        for label in MODELS_WITH_PII:
            try:
                django_apps.get_model(label)
            except (LookupError, ValueError):
                raise CommandError(
                    f'MODELS_WITH_PII incluye «{label}», que no existe.'
                )

    def _write(self, output_dir, filename, targets, exclude, indent,
               carries_pii, passphrase, allow_plaintext):
        """Escribe un volcado, cifrado si lleva PII y hay con qué."""
        if carries_pii and not passphrase and not allow_plaintext:
            return

        encrypting = bool(carries_pii and passphrase)
        target = output_dir / (filename + '.enc' if encrypting else filename)

        buffer = StringIO()

        call_command(
            'dumpdata',
            *targets,
            use_natural_foreign_keys=False,
            use_natural_primary_keys=False,
            exclude=exclude,
            indent=indent,
            stdout=buffer,
        )

        payload = buffer.getvalue().encode('utf-8')

        if encrypting:
            try:
                payload = encrypt(payload, passphrase)
            except BackupCryptoError as error:
                raise CommandError(str(error))

        # Se abre con los permisos ya puestos, no se corrigen después: entre
        # crear el fichero y hacerle chmod hay una ventana en la que cualquiera
        # de la máquina puede abrirlo, y en un hosting compartido esa ventana
        # es el problema entero.
        #
        # `O_BINARY` solo existe en Windows, donde `os.open` abre en modo
        # texto por defecto y traduciria cada salto de linea del fichero cifrado
        # en un retorno de carro mas salto: lo corromperia.
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_BINARY', 0),
            0o600,
        )

        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(payload)

        note = ''

        if encrypting:
            note = ' (cifrado)'
        elif carries_pii:
            note = ' (SIN CIFRAR: lleva datos personales en claro)'

        style = self.style.WARNING if (
            carries_pii and not encrypting) else self.style.SUCCESS

        self.stdout.write(style(f'✔ {target.resolve()}{note}'))

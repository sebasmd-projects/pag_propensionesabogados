# apps/common/utils/tests/test_requirements_export.py
"""
``manage.py check_requirements``: que lo instalado sea lo declarado.

En pag manda ``requirements.txt`` (lo que instala produccion con ``pip``);
``pyproject.toml`` y ``uv.lock`` son de local y estan desactualizados. El
comando compara tres cosas: lo instalado en este entorno contra
``requirements.txt``, ``pyproject.toml`` contra ``requirements.txt``, y que el
grupo de desarrollo (``bandit``, ``pip-audit``, ``safety``) no se cuele en el
servidor por un ``uv export`` sin ``--no-dev``.

Se le da un proyecto de mentira en vez de tocar los ficheros de verdad: una
prueba que reescribe un fichero del repositorio y falla a mitad lo deja roto.
"""

import shutil
import tempfile
import tomllib
from importlib import metadata
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase

ROOT = Path(settings.BASE_DIR)


def installed(name: str) -> str:
    return metadata.version(name)


class FakeProjectMixin:

    def fake_project(self, pyproject: str, requirements: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)

        (directory / 'pyproject.toml').write_text(pyproject, encoding='utf-8')
        (directory / 'requirements.txt').write_text(
            requirements, encoding='utf-8')

        return directory

    def report(self, directory: Path, **options) -> str:
        out = StringIO()

        with self.settings(BASE_DIR=directory):
            try:
                call_command('check_requirements', stdout=out, **options)
            except SystemExit as stop:
                out.write(f'\n[exit {stop.code}]')

        return out.getvalue()


class TheInstalledEnvironmentIsComparedTests(FakeProjectMixin, SimpleTestCase):

    PYPROJECT = '[project]\ndependencies = ["django"]\n'

    def test_a_missing_package_is_named(self):
        directory = self.fake_project(
            self.PYPROJECT, 'paquete-que-no-existe-xyz==1.0.0\n')

        text = self.report(directory)

        self.assertIn('NO instalado: paquete-que-no-existe-xyz', text)

    def test_a_different_version_says_both(self):
        directory = self.fake_project(self.PYPROJECT, 'django==0.0.1\n')

        text = self.report(directory)

        self.assertIn('django: requirements.txt pide ==0.0.1', text)
        self.assertIn(f'hay {installed("django")}', text)

    def test_the_installed_version_is_not_flagged(self):
        directory = self.fake_project(
            self.PYPROJECT, f'django=={installed("django")}\n')

        text = self.report(directory)

        self.assertIn('Todo lo fijado esta instalado', text)
        self.assertNotIn('NO instalado', text)

    def test_an_unpinned_line_only_needs_to_be_installed(self):
        directory = self.fake_project(self.PYPROJECT, 'django\n')

        self.assertIn('Todo lo fijado esta instalado', self.report(directory))

    def test_names_are_compared_the_way_pypi_does(self):
        """`typing_extensions` y `typing-extensions` son el mismo paquete."""
        directory = self.fake_project(
            '[project]\ndependencies = ["typing-extensions"]\n',
            f'typing_extensions=={installed("typing-extensions")}\n')

        text = self.report(directory)

        self.assertNotIn('NO instalado', text)
        self.assertIn('Todo lo fijado esta instalado', text)

    def test_a_marker_that_does_not_apply_is_not_a_missing_package(self):
        directory = self.fake_project(
            self.PYPROJECT,
            'paquete-solo-de-otro-sistema==1.0; sys_platform == "nada"\n')

        self.assertNotIn('NO instalado', self.report(directory))

    def test_strict_exits_with_a_code_when_something_differs(self):
        directory = self.fake_project(self.PYPROJECT, 'django==0.0.1\n')

        self.assertIn('[exit 1]', self.report(directory, strict=True))

    def test_strict_is_quiet_when_all_is_well(self):
        directory = self.fake_project(
            self.PYPROJECT, f'django=={installed("django")}\n')

        self.assertNotIn('[exit', self.report(directory, strict=True))

    def test_a_missing_requirements_file_is_said(self):
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)

        self.assertIn('No se encontro', self.report(directory))


class TheDeclaredListsAreComparedTests(FakeProjectMixin, SimpleTestCase):

    def test_what_pyproject_declares_and_requirements_lacks_is_named(self):
        directory = self.fake_project(
            '[project]\ndependencies = ["django", "pandas", "psycopg2"]\n',
            f'django=={installed("django")}\n')

        text = self.report(directory)

        self.assertIn('ausentes de requirements.txt (2): pandas, psycopg2', text)

    def test_it_does_not_consult_uv_lock(self):
        directory = self.fake_project(
            '[project]\ndependencies = ["django"]\n',
            f'django=={installed("django")}\n')

        self.assertIn('uv.lock no se consulta', self.report(directory))

    def test_the_dev_group_leaking_into_requirements_is_reported(self):
        """
        Un `uv export` sin `--no-dev` mete `bandit`, `pip-audit` y `safety` en
        el servidor, con todo lo que arrastran.
        """
        directory = self.fake_project(
            '[project]\n'
            'dependencies = ["django>=5.2"]\n'
            '\n'
            '[dependency-groups]\n'
            'dev = ["bandit>=1.9.4", "safety>=3.8.1"]\n',
            f'django=={installed("django")}\nbandit==1.9.4\nsafety==3.8.1\n')

        text = self.report(directory)

        self.assertIn('Herramientas de desarrollo', text)
        self.assertIn('bandit', text)
        self.assertIn('--no-dev', text)

    def test_it_stays_quiet_about_dev_tools_when_they_are_not_there(self):
        directory = self.fake_project(
            '[project]\n'
            'dependencies = ["django"]\n'
            '\n'
            '[dependency-groups]\n'
            'dev = ["bandit>=1.9.4"]\n',
            f'django=={installed("django")}\n')

        self.assertNotIn('Herramientas de desarrollo', self.report(directory))


class TheRealFilesTests(SimpleTestCase):
    """Los ficheros del repositorio, tal cual estan."""

    def test_requirements_txt_has_no_development_tools(self):
        data = tomllib.loads(
            (ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
        dev = set()

        for group in (data.get('dependency-groups') or {}).values():
            dev.update(
                line.split('>')[0].split('=')[0].split('[')[0].strip().lower()
                for line in group if isinstance(line, str))

        lines = (ROOT / 'requirements.txt').read_text(
            encoding='utf-8').splitlines()
        exported = {
            line.split('==')[0].split('[')[0].strip().lower()
            for line in lines
            if line.strip() and not line.strip().startswith(('#', '-'))
        }

        self.assertEqual(sorted(dev & exported), [], (
            'requirements.txt lleva herramientas de desarrollo; reexporta con '
            '`uv export --no-dev --format=requirements-txt`'))

    def test_every_line_of_requirements_txt_parses(self):
        """Una linea que no se lee es un paquete que nadie comprueba."""
        from packaging.requirements import Requirement

        for line in (ROOT / 'requirements.txt').read_text(
                encoding='utf-8').splitlines():
            line = line.strip()

            if line and not line.startswith(('#', '-')):
                Requirement(line)

    def test_the_command_runs_on_the_real_project(self):
        out = StringIO()
        call_command('check_requirements', stdout=out)

        self.assertIn('Fijadas en requirements.txt', out.getvalue())
        self.assertIn('2. pyproject.toml contra requirements.txt',
                      out.getvalue())

# apps/common/utils/management/commands/check_requirements.py
"""
Que lo instalado sea lo que declara ``requirements.txt``, y que las otras
listas de dependencias no le lleven la contraria.

En pag manda ``requirements.txt``: es lo que instala **produccion** con
``pip`` (en cPanel no hay ``uv``). ``pyproject.toml`` y ``uv.lock`` son de
local, y estan **desactualizados**: ``uv lock --check`` pide regenerar el
bloqueo y ``pyproject.toml`` declara cinco paquetes que ``requirements.txt`` no
lleva (ver abajo). Por eso este comando no toma el lock como referencia; se
limita a decir donde discrepan.

Tres comprobaciones, de mayor a menor importancia:

1. **Lo instalado en este entorno contra ``requirements.txt``**: paquetes que
   faltan y versiones distintas de la fijada. Es la que importa en el
   servidor: ``pip-audit`` mira lo instalado, asi que si lo instalado no es lo
   declarado, ni el informe de vulnerabilidades ni el codigo que se probo son
   los que corren. Se lanza donde corre la aplicacion.
2. **``pyproject.toml`` contra ``requirements.txt``**: lo declarado en
   ``pyproject.toml`` que el servidor no instalaria. Un paso manual es un paso
   que se olvida, y el sintoma aparece lejos de la causa (una ``ImportError``
   en tiempo de ejecucion).
3. **El grupo de desarrollo** (``[dependency-groups]``) **no debe aparecer en
   ``requirements.txt``**: un ``uv export`` sin ``--no-dev`` mete
   ``bandit``, ``pip-audit`` y ``safety`` en el servidor.

No arregla nada por su cuenta: reexportar o reinstalar es una decision, y
hacerlo solo desde un comando seria peor que el problema.

    manage.py check_requirements
    manage.py check_requirements --strict   # codigo != 0 si hay discrepancias
"""

import re
import tomllib
from importlib import metadata
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# "django-redis>=5.4" -> "django-redis";  "redis==8.1.0 \" -> "redis"
NAME = re.compile(r'^[A-Za-z0-9._-]+')

# Normaliza como hace PyPI: guiones, puntos y guiones bajos son lo mismo.
SEPARATORS = re.compile(r'[-_.]+')


def normalize(name: str) -> str:
    return SEPARATORS.sub('-', name.strip().lower())


class Command(BaseCommand):
    help = (
        'Comprueba que el entorno instalado coincida con requirements.txt (lo '
        'que instala produccion con pip) y que pyproject.toml no declare '
        'paquetes que produccion no instalaria.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Sale con codigo distinto de cero si hay discrepancias.',
        )

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR)
        problems = 0

        requirements = self._from_requirements(root / 'requirements.txt')

        if requirements is None:
            if options['strict']:
                raise SystemExit(1)
            return None

        self.stdout.write(
            f'Fijadas en requirements.txt: {len(requirements)}'
        )

        problems += self._check_installed(requirements)
        problems += self._check_pyproject(root / 'pyproject.toml', requirements)

        self.stdout.write('')

        if not problems:
            self.stdout.write(self.style.SUCCESS(
                'Lo instalado es lo declarado, y pyproject.toml no pide nada '
                'que produccion no instale.'
            ))
            return None

        self.stdout.write(self.style.ERROR(f'{problems} discrepancia(s).'))

        if options['strict']:
            raise SystemExit(1)

        return None

    # ------------------------------------------------------------------
    def _check_installed(self, requirements) -> int:
        """Lo instalado contra lo que fija ``requirements.txt``."""
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            '1. Entorno instalado contra requirements.txt'
        ))

        installed = {}

        for dist in metadata.distributions():
            name = dist.metadata['Name']

            if name:
                installed.setdefault(normalize(name), dist.version)

        missing, different = [], []

        for name, requirement in sorted(requirements.items()):
            if requirement is None:
                continue

            # Un marcador de entorno que no aplica aqui (`; sys_platform ==
            # "win32"`) no es un paquete que falte.
            if requirement.marker is not None and \
                    not requirement.marker.evaluate():
                continue

            version = installed.get(name)

            if version is None:
                missing.append(name)
            elif requirement.specifier and \
                    not requirement.specifier.contains(version,
                                                       prereleases=True):
                different.append((name, str(requirement.specifier), version))

        if not missing and not different:
            self.stdout.write(self.style.SUCCESS(
                '   Todo lo fijado esta instalado en la version fijada.'
            ))
            return 0

        for name in missing:
            self.stdout.write(self.style.ERROR(f'   NO instalado: {name}'))

        for name, wanted, found in different:
            self.stdout.write(self.style.ERROR(
                f'   {name}: requirements.txt pide {wanted} y hay {found}'
            ))

        self.stdout.write(
            '   Se arregla en este entorno con: '
            'pip install -r requirements.txt   (o, con uv, '
            'uv pip install -r requirements.txt). Si es tu maquina de '
            'desarrollo y no lo quieres tocar, tenlo presente: lo que pruebas '
            'no es lo que correra en produccion.'
        )

        return len(missing) + len(different)

    def _check_pyproject(self, path: Path, requirements) -> int:
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            '2. pyproject.toml contra requirements.txt'
        ))

        data = self._load_toml(path)

        if data is None:
            return 0

        declared = {
            normalize(match.group(0))
            for line in data.get('project', {}).get('dependencies', [])
            if (match := NAME.match(line.strip()))
        }

        problems = 0
        absent = sorted(declared - set(requirements))

        if absent:
            problems += len(absent)
            self.stdout.write(self.style.ERROR(
                f'   Declaradas en pyproject.toml y ausentes de '
                f'requirements.txt ({len(absent)}): {", ".join(absent)}'
            ))
            self.stdout.write(
                '   Produccion instala con pip desde requirements.txt: estas '
                'no llegarian al servidor. Si son de verdad necesarias, '
                'anadelas a requirements.txt; si son solo de desarrollo '
                'local, sacalas de [project].dependencies.'
            )

        leaked = sorted(self._dev_tools(data) & set(requirements))

        if leaked:
            problems += len(leaked)
            self.stdout.write(self.style.ERROR(
                'Herramientas de desarrollo en requirements.txt: '
                + ', '.join(leaked)
            ))
            self.stdout.write(
                '   El export se hizo sin `--no-dev`: produccion instalaria '
                'tambien el grupo de desarrollo y lo que arrastra. Se '
                'arregla con `uv export --no-dev --format=requirements-txt`.'
            )

        if not problems:
            self.stdout.write(self.style.SUCCESS(
                '   Nada declarado en pyproject.toml falta en '
                'requirements.txt, y ninguna herramienta de desarrollo se '
                'ha colado.'
            ))

        self.stdout.write(
            '   (uv.lock no se consulta: esta desactualizado respecto a '
            'requirements.txt; regenerarlo con `uv lock` es una decision '
            'aparte.)'
        )

        return problems

    # ------------------------------------------------------------------
    def _load_toml(self, path: Path):
        if not path.exists():
            self.stdout.write(self.style.WARNING(f'   No se encontro {path}.'))
            return None

        try:
            return tomllib.loads(path.read_text(encoding='utf-8'))
        except tomllib.TOMLDecodeError as error:
            self.stdout.write(self.style.ERROR(
                f'   {path} no es TOML valido: {error}'
            ))
            return None

    def _dev_tools(self, data: dict) -> set:
        """
        Los nombres declarados en ``[dependency-groups]``.

        Sirven de marcador: si alguno aparece en ``requirements.txt``, el
        export se hizo sin ``--no-dev``.
        """
        names = set()

        for group in (data.get('dependency-groups') or {}).values():
            for line in group:
                if isinstance(line, str) and (match := NAME.match(line.strip())):
                    names.add(normalize(match.group(0)))

        return names

    def _from_requirements(self, path: Path):
        """``{nombre: Requirement}`` de las lineas de requirements.txt."""
        from packaging.requirements import InvalidRequirement, Requirement

        if not path.exists():
            self.stdout.write(self.style.ERROR(
                f'No se encontro {path}. Produccion no tendria que instalar.'
            ))
            return None

        found = {}

        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()

            # Se ignoran comentarios, opciones (-r, --hash...) y continuaciones.
            if not line or line.startswith(('#', '-')):
                continue

            # Un comentario al final de la linea.
            line = line.split(' #', 1)[0].strip().rstrip('\\').strip()

            try:
                requirement = Requirement(line)
            except InvalidRequirement:
                match = NAME.match(line)

                if match:
                    found[normalize(match.group(0))] = None

                continue

            found[normalize(requirement.name)] = requirement

        return found

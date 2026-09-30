"""
Red de seguridad: consultas con bloqueo que no funcionan en MySQL/MariaDB.

Produccion usa MySQL/MariaDB, que no admite `FOR UPDATE OF`, `NOWAIT`,
`SKIP LOCKED` (segun version) ni `FOR NO KEY UPDATE`. En local se prueba con
PostgreSQL o SQLite, donde esas opciones pasan sin queja y el fallo solo
aparece en produccion.
"""
import ast
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_KWARGS = ('of', 'no_key', 'skip_locked', 'nowait')


def _is_excluded(path):
    parts = path.relative_to(ROOT).parts
    return (
        'migrations' in parts
        or 'tests' in parts
        or path.name.startswith('test_')
        or path.name == 'tests.py'
    )


def _offences():
    found = []
    for base in ('apps', 'app_core'):
        for path in sorted((ROOT / base).rglob('*.py')):
            if _is_excluded(path):
                continue
            try:
                tree = ast.parse(path.read_text(encoding='utf-8'))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == 'select_for_update'):
                    continue
                for kw in node.keywords:
                    if kw.arg in FORBIDDEN_KWARGS:
                        found.append(
                            f'{path.relative_to(ROOT)}:{node.lineno} '
                            f'select_for_update({kw.arg}=...)')
    return found


class DbPortabilityTests(SimpleTestCase):
    def test_select_for_update_es_portable(self):
        found = _offences()
        self.assertEqual(
            found, [],
            'Produccion usa MySQL/MariaDB, que no admite estas opciones de '
            'select_for_update() (of=, no_key=, skip_locked=, nowait=) y '
            'lanza NotSupportedError. Usa select_for_update() a secas y sin '
            'select_related en la consulta bloqueada:\n' + '\n'.join(found))

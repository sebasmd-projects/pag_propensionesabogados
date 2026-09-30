"""
Pruebas de la lectura del entorno (`app_core/env.py`).

Lo que de verdad se protege aqui no es el formato del mensaje, sino que la
lista no se quede vieja: `settings.py` sigue creciendo, y una variable nueva
leida sin valor por defecto que nadie declare vuelve al error de antes --el
`int() argument must be a string` que no nombra nada--. Por eso la primera
prueba lee el propio `settings.py` y exige que cada lectura sin defecto este
decidida: obligatoria, obligatoria segun el motor, o prescindible con su
motivo escrito.
"""

import re
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from app_core import env

SETTINGS = Path(__file__).resolve().parent.parent / 'settings.py'
ENV_EXAMPLE = Path(__file__).resolve().parent.parent.parent / env.ENV_EXAMPLE

# `os.getenv('NOMBRE')`, `env_int('NOMBRE')` o `env_list('NOMBRE')` sin segundo
# argumento. Con defecto no hace falta declarar nada: el defecto ya es la
# respuesta a que falte.
WITHOUT_DEFAULT = re.compile(
    r"(?:os\.getenv|env_int|env_list)\(\s*'([A-Z0-9_]+)'\s*\)"
)


def read_settings() -> str:
    return SETTINGS.read_text(encoding='utf-8')


def declared() -> set:
    return (
        set(env.REQUIRED)
        | set(env.REQUIRED_UNLESS_SQLITE)
        | set(env.OPTIONAL_WITHOUT_DEFAULT)
    )


def complete_environment(engine='django.db.backends.postgresql') -> dict:
    """Un entorno que pasa la comprobacion, para partir de el y quitar cosas."""
    environ = {name: 'valor' for name in env.REQUIRED}
    environ.update({name: 'valor' for name in env.REQUIRED_UNLESS_SQLITE})
    environ['DB_ENGINE'] = engine
    return environ


class SettingsCoverageTests(SimpleTestCase):
    """Que la lista siga cubriendo lo que `settings.py` lee de verdad."""

    def test_toda_lectura_sin_defecto_esta_decidida(self):
        leidas = set(WITHOUT_DEFAULT.findall(read_settings()))
        sin_decidir = sorted(leidas - declared())

        self.assertEqual(
            sin_decidir, [],
            'settings.py lee estas variables sin valor por defecto y no estan '
            'declaradas en app_core/env.py. Decide cada una: a REQUIRED (o a '
            'REQUIRED_UNLESS_SQLITE) si su ausencia impide arrancar, o a '
            'OPTIONAL_WITHOUT_DEFAULT con el motivo escrito de por que no. '
            f'Sin decidir: {sin_decidir}'
        )

    def test_no_quedan_entradas_de_variables_que_ya_nadie_lee(self):
        fuente = read_settings()
        huerfanas = sorted(
            name for name in declared()
            if f"'{name}'" not in fuente and f'"{name}"' not in fuente
        )

        self.assertEqual(
            huerfanas, [],
            'Estas variables estan declaradas en app_core/env.py pero '
            f'settings.py ya no las lee: {huerfanas}'
        )

    def test_allowed_empty_solo_nombra_variables_conocidas(self):
        desconocidas = sorted(env.ALLOWED_EMPTY - declared())

        self.assertEqual(desconocidas, [], f'ALLOWED_EMPTY: {desconocidas}')

    def test_ninguna_variable_esta_en_dos_listas(self):
        self.assertEqual(
            set(env.REQUIRED) & set(env.OPTIONAL_WITHOUT_DEFAULT), set()
        )
        self.assertEqual(
            set(env.REQUIRED) & set(env.REQUIRED_UNLESS_SQLITE), set()
        )
        self.assertEqual(
            set(env.REQUIRED_UNLESS_SQLITE)
            & set(env.OPTIONAL_WITHOUT_DEFAULT), set()
        )

    def test_cada_declaracion_lleva_su_motivo_escrito(self):
        for grupo in (
            env.REQUIRED, env.REQUIRED_UNLESS_SQLITE,
            env.OPTIONAL_WITHOUT_DEFAULT,
        ):
            for name, reason in grupo.items():
                with self.subTest(name=name):
                    self.assertTrue(
                        reason and len(reason) > 20,
                        f'{name} necesita una explicacion util, no una etiqueta'
                    )


class MissingVariablesTests(SimpleTestCase):

    def test_un_entorno_completo_no_echa_nada_en_falta(self):
        self.assertEqual(env.missing_variables(complete_environment()), [])

    def test_la_que_falta_sale_por_su_nombre(self):
        environ = complete_environment()
        del environ['DB_PORT']

        faltan = dict(env.missing_variables(environ))

        self.assertIn('DB_PORT', faltan)
        self.assertEqual(len(faltan), 1)

    def test_salen_todas_las_que_faltan_de_una_vez(self):
        environ = complete_environment()
        for name in ('DB_PORT', 'DJANGO_EMAIL_PORT', 'FIELD_ENCRYPTION_KEY'):
            del environ[name]

        faltan = dict(env.missing_variables(environ))

        self.assertEqual(
            sorted(faltan),
            ['DB_PORT', 'DJANGO_EMAIL_PORT', 'FIELD_ENCRYPTION_KEY'],
        )

    def test_vacia_cuenta_como_ausente(self):
        environ = complete_environment()
        environ['DB_PORT'] = '   '

        self.assertIn('DB_PORT', dict(env.missing_variables(environ)))

    def test_terminos_de_ataque_vacios_no_valen(self):
        """`'|'.join([''])` seria un patron que casa con todas las rutas."""
        environ = complete_environment()
        environ['COMMON_ATTACK_TERMS'] = ''

        self.assertIn(
            'COMMON_ATTACK_TERMS', dict(env.missing_variables(environ))
        )

    def test_con_sqlite_no_se_piden_puerto_ni_conexion(self):
        environ = complete_environment(engine=env.SQLITE_ENGINE)
        for name in env.REQUIRED_UNLESS_SQLITE:
            del environ[name]

        self.assertEqual(env.missing_variables(environ), [])

    def test_sin_sqlite_si_se_piden(self):
        environ = complete_environment()
        for name in env.REQUIRED_UNLESS_SQLITE:
            del environ[name]

        self.assertEqual(
            sorted(dict(env.missing_variables(environ))),
            sorted(env.REQUIRED_UNLESS_SQLITE),
        )

    def test_lo_opcional_no_se_echa_en_falta(self):
        environ = complete_environment()

        for name in env.OPTIONAL_WITHOUT_DEFAULT:
            environ.pop(name, None)

        self.assertEqual(env.missing_variables(environ), [])


class ErrorMessageTests(SimpleTestCase):

    def test_el_error_nombra_la_variable_y_para_que_sirve(self):
        environ = complete_environment()
        del environ['FIELD_ENCRYPTION_KEY']

        with self.assertRaises(ImproperlyConfigured) as caso:
            env.check_environment(environ)

        mensaje = str(caso.exception)

        self.assertIn('FIELD_ENCRYPTION_KEY', mensaje)
        self.assertIn('PII', mensaje)
        self.assertIn(env.ENV_EXAMPLE, mensaje)

    def test_el_error_las_nombra_todas(self):
        environ = complete_environment()
        for name in ('DB_PORT', 'DJANGO_ALLOWED_HOSTS', 'DJANGO_SECRET_KEY'):
            del environ[name]

        with self.assertRaises(ImproperlyConfigured) as caso:
            env.check_environment(environ)

        mensaje = str(caso.exception)

        for name in ('DB_PORT', 'DJANGO_ALLOWED_HOSTS', 'DJANGO_SECRET_KEY'):
            self.assertIn(name, mensaje)

        self.assertIn('Faltan 3', mensaje)

    def test_una_sola_no_se_anuncia_en_plural(self):
        environ = complete_environment()
        del environ['DB_PORT']

        with self.assertRaises(ImproperlyConfigured) as caso:
            env.check_environment(environ)

        self.assertIn('Falta 1 variable', str(caso.exception))

    def test_un_entorno_completo_no_levanta_nada(self):
        env.check_environment(complete_environment())


class TypedReadersTests(SimpleTestCase):

    def test_env_int_lee_un_entero(self):
        self.assertEqual(env.env_int('N', environ={'N': ' 42 '}), 42)

    def test_env_int_con_defecto_si_falta_o_esta_vacia(self):
        self.assertEqual(env.env_int('N', 15, environ={}), 15)
        self.assertEqual(env.env_int('N', 15, environ={'N': ''}), 15)

    def test_env_int_sin_defecto_nombra_la_variable(self):
        with self.assertRaises(ImproperlyConfigured) as caso:
            env.env_int('DB_PORT', environ={})

        self.assertIn('DB_PORT', str(caso.exception))

    def test_env_int_con_basura_nombra_la_variable_y_el_valor(self):
        with self.assertRaises(ImproperlyConfigured) as caso:
            env.env_int('DB_PORT', environ={'DB_PORT': 'abc'})

        self.assertIn('DB_PORT', str(caso.exception))
        self.assertIn("'abc'", str(caso.exception))

    def test_env_list_parte_recorta_y_descarta_huecos(self):
        self.assertEqual(
            env.env_list('L', environ={'L': ' a, b ,,c,'}), ['a', 'b', 'c']
        )

    def test_env_list_uno_solo_sigue_siendo_una_lista(self):
        self.assertEqual(env.env_list('L', environ={'L': 'a.com'}), ['a.com'])

    def test_env_list_con_defecto_devuelve_una_copia(self):
        default = ['x']
        resultado = env.env_list('L', default, environ={})

        self.assertEqual(resultado, ['x'])
        self.assertIsNot(resultado, default)
        self.assertEqual(env.env_list('L', default, environ={'L': ' , '}), ['x'])

    def test_env_list_sin_defecto_nombra_la_variable(self):
        with self.assertRaises(ImproperlyConfigured) as caso:
            env.env_list('COMMON_ATTACK_TERMS', environ={})

        self.assertIn('COMMON_ATTACK_TERMS', str(caso.exception))


class EnvExampleTests(SimpleTestCase):
    """La plantilla que el error recomienda tiene que servir para arrancar."""

    def test_la_plantilla_existe_donde_dice_el_error(self):
        self.assertTrue(ENV_EXAMPLE.is_file(), env.ENV_EXAMPLE)

    def test_la_plantilla_declara_todas_las_obligatorias(self):
        texto = ENV_EXAMPLE.read_text(encoding='utf-8')
        declaradas = set(re.findall(r'^([A-Z0-9_]+)=', texto, re.MULTILINE))

        obligatorias = set(env.REQUIRED) | set(env.REQUIRED_UNLESS_SQLITE)
        faltan = sorted(obligatorias - declaradas)

        self.assertEqual(
            faltan, [],
            f'{env.ENV_EXAMPLE} no declara: {faltan}. Quien copie la '
            'plantilla se llevara el error que esto pretende evitar.'
        )

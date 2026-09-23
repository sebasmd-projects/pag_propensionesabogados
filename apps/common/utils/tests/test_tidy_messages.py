import tempfile, textwrap
from pathlib import Path
from django.core.management import call_command
from django.test import TestCase, override_settings
from io import StringIO

CATALOGO = '''# Traducciones
msgid ""
msgstr ""
"Language: \\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"

#: apps/x.py:1
msgid "Notifications email"
msgstr "identificación"

#: apps/x.py:2
#, fuzzy
#| msgid "Identification"
msgid "Notifications email 2"
msgstr "identificación"

#: apps/x.py:3
#, fuzzy, python-format
msgid "Al 0 % no es cuota litis"
msgstr ""
"adivinanza larga que gettext copió de otra "
"entrada parecida"

#: apps/x.py:4
msgid "Bien traducida"
msgstr "Bien traducida"
'''

class TidyTests(TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        d = Path(self.dir) / 'es' / 'LC_MESSAGES'
        d.mkdir(parents=True)
        self.po = d / 'django.po'
        self.po.write_text(CATALOGO, encoding='utf-8')

    def run_cmd(self):
        with override_settings(LOCALE_PATHS=[self.dir]):
            call_command('tidy_messages', stdout=StringIO())
        return self.po.read_text(encoding='utf-8')

    def test_vacia_la_adivinanza_de_las_dudosas(self):
        s = self.run_cmd()
        self.assertNotIn('adivinanza larga', s)
        # la entrada dudosa de una linea tambien
        bloque = [b for b in s.split('\n\n') if 'Notifications email 2' in b][0]
        self.assertIn('msgstr ""', bloque)
        self.assertNotIn('identificación', bloque)

    def test_no_toca_las_que_no_eran_dudosas(self):
        s = self.run_cmd()
        self.assertIn('msgstr "Bien traducida"', s)
        bloque = [b for b in s.split('\n\n')
                  if 'msgid "Notifications email"' in b][0]
        self.assertIn('identificación', bloque)

    def test_quita_el_flag_y_el_msgid_anterior(self):
        s = self.run_cmd()
        self.assertNotIn('#, fuzzy', s.split('msgid ""', 1)[1])
        self.assertNotIn('#|', s)

    def test_quita_el_python_format_espurio(self):
        s = self.run_cmd()
        self.assertNotIn('python-format', s)

    def test_rellena_la_cabecera(self):
        s = self.run_cmd()
        self.assertIn('"Language: es\\n"', s)


class ConteoTests(TestCase):
    """
    El recuento del final, que es la unica senal de cuanto queda.

    Una traduccion larga se escribe partida, empezando por `msgstr ""`. Esa
    linea es identica a la de una entrada sin traducir, asi que contarla a
    secas daba por pendientes justo las traducciones mas largas del catalogo.
    """

    CATALOGO = '''msgid ""
msgstr ""
"Language: es\\n"

#: apps/x.py:1
msgid "Larga"
msgstr ""
"Una traducción lo bastante larga como para que polib la parta en varias "
"líneas al guardar el fichero."

#: apps/x.py:2
msgid "Sin traducir"
msgstr ""

#: apps/x.py:3
msgid "Corta"
msgstr "Corta"
'''

    def test_una_traduccion_partida_no_cuenta_como_pendiente(self):
        import tempfile
        from pathlib import Path

        raiz = tempfile.mkdtemp()
        destino = Path(raiz) / 'es' / 'LC_MESSAGES'
        destino.mkdir(parents=True)
        (destino / 'django.po').write_text(self.CATALOGO, encoding='utf-8')

        salida = StringIO()
        with override_settings(LOCALE_PATHS=[raiz]):
            call_command('tidy_messages', stdout=salida)

        self.assertIn('Quedan 1 entradas sin traducir', salida.getvalue())

"""
Deja los catalogos de traduccion como tienen que quedar tras `makemessages`.

Por que hace falta
------------------
`makemessages` deja tres cosas que hacen que una traduccion escrita **no se
use**, y ninguna de las tres da error:

1. **Entradas `fuzzy`.** Cuando una cadena se parece a otra que ya estaba
   traducida, gettext copia aquella traduccion y marca la entrada como
   dudosa. Una entrada `fuzzy` se **ignora en tiempo de ejecucion**: sale el
   texto en ingles, con la traduccion escrita justo debajo. Es el fallo mas
   desconcertante de todos, porque el fichero parece correcto.

   Al quitar el flag, esta orden **vacia tambien la traduccion**, y eso no es
   un exceso de celo: quitarlo a secas convierte la adivinanza de gettext en
   una traduccion que si se usa. Se vio aqui mismo -- «Notifications email»
   heredo «identificacion», y «Para obtener informacion sobre su proceso...»
   heredo el subtitulo del buscador--, y ninguna de las dos daba error: la
   pantalla salia en castellano diciendo otra cosa. Sin traduccion sale el
   ingles, que se ve, se nota y se arregla; con una traduccion equivocada no
   se entera nadie.

2. **`python-format` de mas.** Ese mismo emparejamiento por parecido le pone
   el flag a cadenas que solo llevan un `%` literal --«al 0 % no es cuota
   litis»--. Con el flag puesto, `msgfmt` valida ese `%` como si fuera una
   directiva de formato y **rechaza el fichero entero**: no se compila
   ninguna traduccion, ni las buenas.

3. **Cabeceras sin rellenar**, que dejan `Language` vacio.

Los tres se arreglan siempre igual, asi que estan aqui y no en la cabeza de
quien traduzca la proxima vez.

Uso
---
Despues de `makemessages`, y antes de `compilemessages`::

    manage.py makemessages -l es --no-obsolete
    manage.py tidy_messages
    manage.py compilemessages -l es

Lo que **no** hace: traducir. Las entradas vacias las deja vacias --y vacia
las dudosas-- y las cuenta al final, para que se vea cuanto queda.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

#: Lo que de verdad es un marcador de formato. Un `%` suelto no lo es.
FORMAT_PLACEHOLDER = re.compile(r'%\(|%[sdrf]\b|%%')


class Command(BaseCommand):
    help = (
        'Quita los `fuzzy` --vaciando la traduccion adivinada-- y los '
        '`python-format` espurios que deja `makemessages`, y rellena las '
        'cabeceras.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--language', '-l',
            default='es',
            help='Codigo del idioma a revisar (por defecto, es).',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='No escribe nada; solo dice que habria que arreglar.',
        )

    def handle(self, *args, **options):
        idioma = options['language']
        solo_mirar = options['check']

        catalogos = sorted(
            ruta
            for base in self._locale_paths()
            for ruta in Path(base).glob(f'{idioma}/LC_MESSAGES/*.po')
        )

        if not catalogos:
            self.stdout.write(self.style.WARNING(
                f'No hay catalogos de «{idioma}» en las rutas de traduccion.'
            ))
            return

        total_fuzzy = total_flags = total_vacias = 0

        for ruta in catalogos:
            original = ruta.read_text(encoding='utf-8')
            arreglado, fuzzy, flags = self._tidy(original)
            vacias = self._count_untranslated(arreglado)

            total_fuzzy += fuzzy
            total_flags += flags
            total_vacias += vacias

            if fuzzy or flags:
                verbo = 'habria que quitar' if solo_mirar else 'quitados'
                self.stdout.write(
                    f'{ruta.relative_to(Path.cwd()) if ruta.is_relative_to(Path.cwd()) else ruta}: '
                    f'{verbo} {fuzzy} fuzzy y {flags} flags de formato'
                )

            if not solo_mirar and arreglado != original:
                ruta.write_text(arreglado, encoding='utf-8')

        self._report(total_fuzzy, total_flags, total_vacias, solo_mirar)

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _locale_paths():
        rutas = list(getattr(settings, 'LOCALE_PATHS', []))
        return [r for r in rutas if Path(r).is_dir()]

    @staticmethod
    def _tidy(contenido: str) -> tuple[str, int, int]:
        """Devuelve el catalogo arreglado y cuantos arreglos hizo."""
        # La cabecera lleva su `fuzzy` por convencion y se respeta; lo que se
        # limpia es de la cabecera en adelante.
        corte = contenido.find('msgid ""')
        antes, despues = contenido[:corte], contenido[corte:]

        fuzzy = len(re.findall(r'^#, fuzzy(?:, |\n)', despues, flags=re.M))

        # Primero se vacia la traduccion adivinada de cada entrada dudosa, y
        # despues se quita el flag. Al reves no habria por donde reconocerlas.
        despues = Command._blank_fuzzy(despues)

        # Los `#|` son el msgid anterior que gettext apunta al marcar `fuzzy`;
        # sin el flag no significan nada, y si se dejan a medias rompen el
        # fichero.
        despues = re.sub(r'^#\|.*\n', '', despues, flags=re.M)
        despues = re.sub(r'^#, fuzzy, ', '#, ', despues, flags=re.M)
        despues = re.sub(r'^#, fuzzy\n', '', despues, flags=re.M)

        contenido = antes + despues

        flags = 0
        bloques = contenido.split('\n\n')
        for i, bloque in enumerate(bloques):
            if '#, python-format' not in bloque or 'msgid' not in bloque:
                continue
            texto = '\n'.join(
                l for l in bloque.splitlines()
                if l.startswith(('msgid', 'msgstr', '"'))
            )
            if not FORMAT_PLACEHOLDER.search(texto):
                bloques[i] = bloque.replace('#, python-format\n', '')
                flags += 1
        contenido = '\n\n'.join(bloques)

        contenido = contenido.replace('"Language: \\n"', '"Language: es\\n"', 1)
        contenido = contenido.replace(
            '"Language-Team: LANGUAGE <LL@li.org>\\n"',
            '"Language-Team: Propensiones Abogados\\n"',
            1,
        )
        return contenido, fuzzy, flags

    @staticmethod
    def _blank_fuzzy(contenido: str) -> str:
        """
        Deja vacia la traduccion de las entradas marcadas como dudosas.

        Es lo que evita que quitar el flag ascienda la adivinanza de gettext a
        traduccion buena. Lo que queda es una entrada sin traducir, que sale
        en ingles y que el recuento del final canta.
        """
        bloques = contenido.split('\n\n')

        for i, bloque in enumerate(bloques):
            if not re.search(r'^#, fuzzy(?:,|$)', bloque, flags=re.M):
                continue

            lineas, dentro = [], False

            for linea in bloque.splitlines():
                if linea.startswith('msgstr'):
                    dentro = True
                    # `msgstr[0]`, `msgstr[1]`... en las entradas con plural.
                    lineas.append(re.sub(r'^(msgstr(?:\[\d+\])?) .*',
                                         r'\1 ""', linea))
                    continue

                if dentro:
                    # Las continuaciones `"..."` de la traduccion que se va.
                    if linea.startswith('"'):
                        continue
                    dentro = False

                lineas.append(linea)

            bloques[i] = '\n'.join(lineas)

        return '\n\n'.join(bloques)

    @staticmethod
    def _count_untranslated(contenido: str) -> int:
        """
        Entradas con `msgstr` vacio de verdad, sin contar la cabecera.

        El «de verdad» hace falta porque una traduccion larga se escribe
        partida::

            msgstr ""
            "Consulte el estado y avance de su tramite con Propensiones..."

        Esa primera linea es identica a la de una entrada sin traducir, asi
        que buscarla a secas contaba como pendientes justo las traducciones
        mas largas del catalogo --las que mas trabajo costaron--. Lo que la
        distingue es si despues viene una continuacion entre comillas.
        """
        return sum(
            1
            for bloque in contenido.split('\n\n')[1:]
            if re.search(r'^msgid "(?!")', bloque, flags=re.M)
            and re.search(r'^msgstr(?:\[\d+\])? ""$(?!\n")', bloque,
                          flags=re.M)
        )

    def _report(self, fuzzy, flags, vacias, solo_mirar):
        if solo_mirar and (fuzzy or flags):
            raise SystemExit(
                self.style.ERROR(
                    f'Hay {fuzzy} entradas fuzzy y {flags} flags de formato '
                    f'por arreglar. Ejecuta `manage.py tidy_messages`.'
                )
            )

        if fuzzy or flags:
            self.stdout.write(self.style.SUCCESS(
                f'Listo: {fuzzy} entradas desmarcadas --y vaciadas-- y '
                f'{flags} flags quitados. Ahora, traducir lo que quede y '
                f'`compilemessages`.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                'Los catalogos ya estaban limpios.'
            ))

        if vacias:
            self.stdout.write(self.style.WARNING(
                f'Quedan {vacias} entradas sin traducir.'
            ))

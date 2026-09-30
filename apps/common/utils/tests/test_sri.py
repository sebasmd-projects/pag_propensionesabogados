# apps/common/utils/tests/test_sri.py
"""
Que nada de fuera se ejecute sin comprobar que es lo que decimos que es.

Un `<script src="https://cdn...">` sin `integrity` es una promesa de que el CDN
--y cualquiera que pueda hablar por el-- va a servir siempre el mismo codigo.
En pag hay dos sitios donde eso importa: el gestor (DataTables y pdfmake, con
sesion del despacho y datos de clientes en pantalla) y las paginas de la
documentacion de la API (Swagger UI y ReDoc, solo para personal).

Con `integrity` el navegador compara el hash de lo que recibe con el que esta
escrito en la etiqueta, y si no cuadra **no lo ejecuta**. Es barato y no
depende de confiar en nadie. Los hashes se sacan del fichero **exacto** que
sirve el CDN, con la version fijada en la URL: una URL sin version sigue a la
ultima publicacion, y esa no admite hash porque cambiaria sola.

Esta prueba falla si aparece un tercero nuevo sin firmar o sin estar en las
excepciones de abajo, sea en una plantilla del proyecto o en un `@import` de
CSS.

Lo que no se puede firmar, y por que
------------------------------------
Estan declaradas abajo con su motivo. No se toleran mas: anadir un CDN nuevo
sin `integrity` falla aqui, y si de verdad no se puede firmar, la excepcion se
escribe y se razona en vez de aparecer sola.

    manage.py test apps.common.utils.tests.test_sri \\
        --settings=app_core.settings_test
"""

import collections
import pathlib
import re

from django.conf import settings
from django.test import SimpleTestCase

#: Una etiqueta `<script>` o `<link>` completa. Las comillas se respetan para
#: que un `>` dentro de un atributo (o de una etiqueta de plantilla) no la
#: corte a medias.
TAG = re.compile(
    r'''<(script|link)\b((?:[^>"']|"[^"]*"|'[^']*')*)>''', re.S | re.I)

#: Un atributo `src=` / `href=` con su valor.
ATTRIBUTE = re.compile(
    r'''\b(src|href)\s*=\s*(?:"([^"]*)"|'([^']*)')''', re.I)

#: Un atributo `rel=`.
REL = re.compile(r'''\brel\s*=\s*(?:"([^"]*)"|'([^']*)')''', re.I)

#: Los `<link>` que **cargan** algo ejecutable o que da estilo. Los demas
#: (`canonical`, `alternate`, `preconnect`, `icon`, `manifest`...) no traen
#: codigo: apuntan a una pagina, abren una conexion o son una imagen, y una
#: imagen no puede llevar `integrity`.
LOADING_RELS = ('stylesheet', 'preload', 'modulepreload')

#: Hosts que **no** pueden llevar `integrity`, con la razon por la que no.
#: Cada entrada es una excepcion consciente, no un olvido.
CANNOT_BE_PINNED = {
    'fonts.googleapis.com': (
        'Google Fonts CSS (base.html y la pagina de ReDoc). El contenido de '
        'esa URL cambia segun el navegador que la pide (formatos y '
        'subconjuntos de fuente distintos) y Google lo actualiza sin avisar, '
        'asi que no hay un hash que valga para todos. Es CSS de '
        'tipografias, sin JavaScript. Cerrarlo de verdad es alojar las '
        'fuentes en el propio sitio.'
    ),
    'www.google.com': (
        'reCAPTCHA (formulario de contacto): `api.js` es un cargador mutable '
        'por diseno; Google exige cargarlo de su URL y lo actualiza sin '
        'version, y un hash fijo rompe el captcha en la siguiente '
        'publicacion. Lo inserta el widget de django-recaptcha, no una '
        'plantilla del proyecto, y esta acotado por la CSP (`script-src`, '
        '`frame-src`).'
    ),
    'www.gstatic.com': (
        'reCAPTCHA: los recursos que `api.js` pide a gstatic. Mismo motivo: '
        'los carga el propio script de Google, que no permite fijarlos.'
    ),
    'www.recaptcha.net': (
        'reCAPTCHA en su dominio alternativo (`RECAPTCHA_DOMAIN`); mismo '
        'motivo que www.google.com.'
    ),
}

#: El propio dominio. No es un tercero.
OWN_HOSTS = {
    'propensionesabogados.com',
    'www.propensionesabogados.com',
    'geausa.propensionesabogados.com',
}

#: Terceros que cargan **imagen** y no codigo (no admiten `integrity`); se
#: listan para que la excepcion este escrita, aunque `<img>` no lo mire esta
#: prueba. Ver `docs/SEGURIDAD.md`.
THIRD_PARTY_IMAGES = {
    'tracecertificates.com': 'icono de la plataforma Trace en la cabecera.',
}

BASE = pathlib.Path(settings.BASE_DIR)


def template_files():
    """Todas las plantillas del proyecto: las de las apps y `templates/`."""
    for root in (BASE / 'apps', BASE / 'app_core', BASE / 'templates'):
        yield from sorted(root.rglob('*.html'))


def tags_in(content):
    """``(etiqueta, url, tiene_integrity, rel)`` de cada `<script>`/`<link>`."""
    for match in TAG.finditer(content):
        name, body = match.group(1).lower(), match.group(2)
        attribute = ATTRIBUTE.search(body)

        if attribute is None:
            continue

        url = attribute.group(2) if attribute.group(2) is not None \
            else attribute.group(3)
        rel_match = REL.search(body)
        rel = ((rel_match.group(1) or rel_match.group(2) or '').lower()
               if rel_match else '')

        if name == 'link' and not any(item in rel.split()
                                      for item in LOADING_RELS):
            continue

        yield name, url.strip(), 'integrity=' in body, rel


def host_of(url):
    if url.startswith('//'):
        url = 'https:' + url

    return url.split('/')[2].lower()


def is_external(url):
    return url.startswith(('https://', 'http://', '//'))


def is_dynamic(url):
    """Una URL que se compone con una variable (`{{ swagger_ui_css }}`)."""
    return url.startswith('{{')


def offending_tags():
    """Etiquetas de terceros sin `integrity`, agrupadas por host."""
    found = collections.defaultdict(list)

    for path in template_files():
        content = path.read_text(encoding='utf-8')

        for _name, url, signed, _rel in tags_in(content):
            if signed or not is_external(url):
                continue

            host = host_of(url)

            if host in OWN_HOSTS or host in CANNOT_BE_PINNED:
                continue

            found[host].append(str(path.relative_to(BASE)))

    return found


class EveryThirdPartyAssetIsPinnedTests(SimpleTestCase):

    def test_nothing_loads_unverified(self):
        offenders = offending_tags()

        self.assertEqual(
            dict(offenders), {},
            'estos recursos de terceros se cargan sin comprobar que sean los '
            'esperados; anade integrity="sha384-..." y crossorigin, o si de '
            'verdad no se puede, declaralo en CANNOT_BE_PINNED con su motivo',
        )

    def test_a_new_unsigned_third_party_would_be_caught(self):
        """La prueba de la prueba: si el detector no ve esto, no vale nada."""
        html = ('<script src="https://cdn.nuevo.example/lib.js"></script>'
                '<link rel="stylesheet" href="https://cdn.nuevo.example/a.css">')

        tags = list(tags_in(html))

        self.assertEqual(len(tags), 2)
        for _name, url, signed, _rel in tags:
            self.assertTrue(is_external(url))
            self.assertFalse(signed)
            self.assertNotIn(host_of(url), CANNOT_BE_PINNED)

    def test_a_signed_one_and_a_non_loading_link_are_not_flagged(self):
        html = (
            '<script src="https://cdn.x.example/a.js" integrity="sha384-abc" '
            'crossorigin="anonymous"></script>'
            '<link href="https://x.example/" rel="canonical">'
            '<link rel="preconnect" href="https://fonts.gstatic.com">'
            '<link rel="icon" href="https://x.example/i.png">'
        )

        signed = [tag for tag in tags_in(html)]

        self.assertEqual(len(signed), 1)
        self.assertTrue(signed[0][2])

    def test_a_greater_than_inside_an_attribute_does_not_hide_a_tag(self):
        html = ('<script data-x="a>b" src="https://cdn.x.example/a.js">'
                '</script>')

        self.assertEqual(len(list(tags_in(html))), 1)

    def test_every_signed_tag_also_says_crossorigin(self):
        """
        `integrity` sin `crossorigin` no comprueba nada en recursos de otro
        origen: el navegador los pide en modo `no-cors` y no puede leerlos.
        """
        missing = []

        for path in template_files():
            content = path.read_text(encoding='utf-8')

            for match in TAG.finditer(content):
                body = match.group(2)

                if 'integrity=' in body and 'crossorigin' not in body:
                    missing.append(str(path.relative_to(BASE)))

        self.assertEqual(missing, [])

    def test_the_gestor_scripts_are_the_pinned_ones(self):
        """Lo que el gestor carga de fuera, tal como esta hoy."""
        path = (BASE / 'apps/project/api/platform/case_manager/templates/'
                'case_manager/gestor/partials')
        content = (path / 'datatables_js.html').read_text(encoding='utf-8')
        content += (path / 'datatables.html').read_text(encoding='utf-8')

        external = [tag for tag in tags_in(content) if is_external(tag[1])]

        self.assertEqual(len(external), 4)

        for _name, url, signed, _rel in external:
            self.assertTrue(signed, url)
            self.assertRegex(url, r'@\d|/dt-\d', f'{url} sin version fija')


class NothingIsLoadedFromAnUnpinnedVersionTests(SimpleTestCase):
    """
    Una URL sin version sigue a la ultima publicacion del paquete: hoy sirve
    una cosa y manana otra, sin que nadie lo decida. Y ademas no admite
    `integrity`, porque el hash cambiaria solo.
    """

    def test_jsdelivr_urls_carry_a_version(self):
        unpinned = []

        for path in template_files():
            for _name, url, _signed, _rel in tags_in(
                    path.read_text(encoding='utf-8')):
                if not url.startswith('https://cdn.jsdelivr.net/npm/'):
                    continue

                package = url[len('https://cdn.jsdelivr.net/npm/'):]

                if '@' not in package.split('/')[0]:
                    unpinned.append(f'{url}  ({path.relative_to(BASE)})')

        self.assertEqual(unpinned, [], 'sin version, la URL sigue a la ultima')

    def test_swagger_and_redoc_are_pinned_in_the_settings(self):
        """
        drf-spectacular trae `@latest` por defecto; se fija a una version
        exacta porque las plantillas de `templates/drf_spectacular/` llevan los
        hashes de esa version.
        """
        spectacular = settings.SPECTACULAR_SETTINGS

        for key in ('SWAGGER_UI_DIST', 'SWAGGER_UI_FAVICON_HREF',
                    'REDOC_DIST'):
            value = spectacular.get(key, '')

            self.assertNotIn('latest', value, key)
            self.assertRegex(value, r'@\d+\.\d+\.\d+', key)

    def test_the_dynamic_urls_of_the_docs_pages_are_signed(self):
        """
        Las plantillas de Swagger y ReDoc componen la URL con una variable
        (`{{ swagger_ui_bundle }}`), asi que el detector de arriba no las ve
        como externas. Aqui se exige que cada una lleve su `integrity`.
        """
        root = BASE / 'templates' / 'drf_spectacular'
        seen = 0

        for path in sorted(root.glob('*.html')):
            for _name, url, signed, _rel in tags_in(
                    path.read_text(encoding='utf-8')):
                if not is_dynamic(url):
                    continue

                # La URL de `script_url` es la del propio proyecto (un script
                # del esquema que sirve la vista), no del CDN.
                if 'script_url' in url:
                    continue

                seen += 1
                self.assertTrue(signed, f'{path.name}: {url} sin integrity')

        self.assertEqual(seen, 5, 'cambio el numero de recursos de las paginas')


class CssImportsTests(SimpleTestCase):

    def test_no_stylesheet_imports_from_a_third_party(self):
        """`@import url(https://...)` en un CSS propio: sin `integrity` posible."""
        offenders = []
        pattern = re.compile(r'@import\s+(?:url\()?["\']?(https?:)?//', re.I)

        for path in sorted((BASE / 'public').rglob('*.css')):
            if pattern.search(path.read_text(encoding='utf-8', errors='ignore')):
                offenders.append(str(path.relative_to(BASE)))

        self.assertEqual(offenders, [])


class TheExceptionsAreDeclaredTests(SimpleTestCase):
    """Una excepcion sin motivo escrito es un olvido con mejor aspecto."""

    def test_every_exception_has_a_reason(self):
        for host, reason in CANNOT_BE_PINNED.items():
            self.assertGreater(
                len(reason), 60,
                f'{host} esta exento sin explicar por que',
            )

    def test_every_exception_is_still_used_or_documented(self):
        """
        Una excepcion que ya no hace falta se quita: si no, el listado deja de
        decir la verdad. reCAPTCHA no sale en las plantillas del proyecto (lo
        pone el widget), asi que se comprueba que sigue en la CSP.
        """
        template_hosts = set()

        for path in template_files():
            for _name, url, _signed, _rel in tags_in(
                    path.read_text(encoding='utf-8')):
                if is_external(url):
                    template_hosts.add(host_of(url))

        policy = str(settings.CONTENT_SECURITY_POLICY_REPORT_ONLY)

        for host in CANNOT_BE_PINNED:
            if host in template_hosts:
                continue

            self.assertTrue(
                host in policy or host == 'www.recaptcha.net',
                f'{host} esta exento pero ya no se carga ni esta en la CSP',
            )

    def test_the_images_are_listed_with_a_reason(self):
        for host, reason in THIRD_PARTY_IMAGES.items():
            self.assertTrue(reason)

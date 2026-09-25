"""
El tema claro/oscuro, que vive en un solo atributo del `<html>`.

Lo que se prueba aqui no es como se ve --eso no se prueba con `assertContains`
y se mira en el navegador-- sino las tres cosas que, si se rompen, no dan
error y dejan el modo oscuro medio puesto:

* que la hoja y el interruptor llegan a **todas** las paginas, porque van en
  `raw.html` y no en cada plantilla;
* que el tema se decide **antes de pintar**, que es lo que evita el parpadeo
  blanco al cargar;
* que `theme.css` se carga **despues** de `main.css`, o la paleta oscura
  perderia la cascada contra la clara y no se notaria nada.
"""

from django.test import TestCase
from django.urls import reverse


class ThemeWiringTests(TestCase):
    """Que el tema llega a las paginas del sitio, no solo a una."""

    def paginas(self):
        return [
            reverse('core:index'),
            reverse('case_manager:public_query'),
            reverse('account:login'),
        ]

    def test_todas_las_paginas_traen_la_hoja_y_el_interruptor(self):
        for ruta in self.paginas():
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)

                self.assertContains(respuesta, 'custom/css/theme.css')
                self.assertContains(respuesta, 'custom/js/theme.js')

    def test_el_tema_se_decide_antes_de_pintar(self):
        """
        El trozo que lo aplica va en linea en el `<head>`.

        Si se moviera a `theme.js` --que lleva `defer` y va al final-- la
        pagina saldria clara y cambiaria a oscura a la vista. Ese parpadeo
        blanco molesta justo a quien elige el modo oscuro.
        """
        html = self.client.get(reverse('core:index')).content.decode()
        cabeza = html.split('</head>')[0]

        self.assertIn('data-bs-theme', cabeza)
        self.assertIn('prefers-color-scheme: dark', cabeza)

    def test_la_hoja_del_tema_va_despues_de_la_del_sitio(self):
        """
        Las dos declaran las mismas variables y ganan por orden. Al reves, la
        paleta clara pisaria a la oscura y el interruptor no haria nada
        visible.
        """
        html = self.client.get(reverse('core:index')).content.decode()

        self.assertLess(
            html.index('custom/css/main.css'),
            html.index('custom/css/theme.css'),
        )

    def test_leer_el_almacenamiento_no_puede_tumbar_la_pagina(self):
        """
        En navegacion privada o con las cookies de terceros desactivadas,
        `localStorage.getItem` **lanza** en vez de devolver null. Sin el
        `try`, esa excepcion dejaria la pagina sin `<head>`.
        """
        html = self.client.get(reverse('core:index')).content.decode()
        cabeza = html.split('</head>')[0]

        self.assertIn('try { tema = localStorage.getItem("tema"); }', cabeza)


class UtilidadesFijasEnOscuroTests(TestCase):
    """
    Las clases de Bootstrap que **no** cambian solas con el modo oscuro.

    Bootstrap 5.3 redefine para el modo oscuro los colores del cuerpo y las
    familias `*-bg-subtle` y `*-text-emphasis`, pero deja `--bs-light-rgb`
    igual en los dos modos. Asi que `.bg-light` pinta el mismo gris casi
    blanco de siempre, y el texto que hay dentro hereda el claro del tema:
    gris claro sobre blanco. Es lo que dejo ilegibles las novedades del
    expediente, y volveria a pasar en cuanto alguien escriba `bg-light` otra
    vez --que es una clase normal de Bootstrap, no un error--.

    Se comprueba la hoja y no una pagina porque el puente vive en la hoja: es
    lo que hace que la proxima tarjeta con `bg-light` nazca bien sin que nadie
    se acuerde de esto.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from pathlib import Path

        from django.conf import settings

        cls.hoja = next(
            Path(carpeta, 'assets/custom/css/theme.css')
            for carpeta in [*settings.STATICFILES_DIRS, settings.STATIC_ROOT]
            if Path(carpeta, 'assets/custom/css/theme.css').is_file()
        ).read_text(encoding='utf-8')

    def test_el_gris_claro_se_oscurece(self):
        oscuro = self.hoja.split(':root[data-bs-theme="dark"]')

        self.assertTrue(
            any('--bs-light-rgb' in trozo for trozo in oscuro[1:]),
            'Sin redefinir `--bs-light-rgb`, `bg-light` deja un bloque blanco '
            'con el texto claro del tema encima.',
        )

    def test_el_texto_de_text_bg_light_deja_de_ser_negro(self):
        """
        `text-bg-light` ademas fija `color: #000`. Cambiarle solo el fondo lo
        deja negro sobre gris oscuro, que se lee igual de mal.
        """
        self.assertIn('.text-bg-light', self.hoja)
        bloque = self.hoja.split('.text-bg-light')[1].split('}')[0]

        self.assertIn('var(--bs-body-color)', bloque)

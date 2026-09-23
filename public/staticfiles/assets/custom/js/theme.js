/*
 * El interruptor de claro/oscuro.
 *
 * La eleccion se guarda en `localStorage`; si no hay ninguna, manda lo que
 * diga el sistema operativo (`prefers-color-scheme`) y se sigue moviendo con
 * el mientras nadie toque el boton. Quien pulsa el boton elige, y a partir de
 * ahi su eleccion pesa mas que el sistema.
 *
 * El tema se aplica **antes de pintar**, desde un trozo suelto en el `<head>`
 * (ver `raw.html`); esto de aqui es solo lo que hace falta despues: el boton y
 * el seguimiento del sistema. Si se aplicara aqui, la pagina saldria clara y
 * pasaria a oscura a la vista, que es el parpadeo blanco que molesta
 * precisamente a quien elige el modo oscuro.
 */
(function () {
  "use strict";

  var CLAVE = "tema";

  function guardado() {
    // En navegacion privada o con el almacenamiento bloqueado, `localStorage`
    // lanza en vez de devolver null. Un tema no es motivo para romper la
    // pagina: se sigue sin recordar nada.
    try {
      return window.localStorage.getItem(CLAVE);
    } catch (e) {
      return null;
    }
  }

  function recordar(tema) {
    try {
      window.localStorage.setItem(CLAVE, tema);
    } catch (e) {
      /* se aplica igual, solo que no se recuerda */
    }
  }

  function aplicar(tema) {
    document.documentElement.setAttribute("data-bs-theme", tema);

    document.querySelectorAll(".tema-boton").forEach(function (boton) {
      boton.setAttribute("aria-pressed", String(tema === "dark"));
    });
  }

  function actual() {
    return document.documentElement.getAttribute("data-bs-theme") === "dark"
      ? "dark"
      : "light";
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".tema-boton").forEach(function (boton) {
      boton.setAttribute("aria-pressed", String(actual() === "dark"));

      boton.addEventListener("click", function (evento) {
        // Los botones del menu son `<a href="#">` en la cabecera del sitio,
        // y sin esto la pagina salta al principio al cambiar de tema.
        evento.preventDefault();

        var siguiente = actual() === "dark" ? "light" : "dark";

        aplicar(siguiente);
        recordar(siguiente);
      });
    });
  });

  // Seguir al sistema mientras nadie haya elegido a mano.
  if (window.matchMedia) {
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", function (evento) {
        if (!guardado()) {
          aplicar(evento.matches ? "dark" : "light");
        }
      });
  }
})();

/*
 * Portal publico de consulta de procesos.
 *
 * Lo que queda de JavaScript en esta pagina, y por que es tan poco.
 *
 * La version anterior tenia mil cuatrocientas lineas aqui dentro, y no eran
 * de interfaz: eran la aplicacion entera. El almacen de expedientes
 * (`localStorage.propDemo`), la comprobacion de la clave del cliente, el
 * panel de administracion, la contrasena administrativa y su valor por
 * defecto, los totales del panel economico y la generacion del paz y salvo.
 * Todo eso decidia el navegador del visitante sobre datos que el navegador
 * del visitante ya tenia, que es otra forma de decir que no decidia nadie.
 *
 * Ahora eso vive en el servidor. Aqui solo queda lo que de verdad es del
 * navegador: ensenar u ocultar la clave mientras se escribe, y no dejar
 * mandar el formulario dos veces.
 *
 * Si algo de lo que se borro hace falta, va al servidor. No vuelve aqui.
 */

(function () {
  'use strict';

  /* Ver la clave mientras se teclea. Es comodidad, no seguridad: el valor ya
     esta en el campo, esto solo cambia como lo pinta el navegador.
     Bootstrap no trae este boton hecho; el resto del formulario si. */
  function conmutarClave() {
    var campo = document.getElementById('claveCliente');
    var boton = document.getElementById('verClaveCliente');
    if (!campo || !boton) {
      return;
    }

    boton.addEventListener('click', function () {
      var oculta = campo.type === 'password';
      campo.type = oculta ? 'text' : 'password';
      boton.setAttribute('aria-pressed', String(oculta));
      /* El icono es de Bootstrap Icons, que ya carga el sitio: solo cambia
         la clase. `aria-pressed` es lo que lo cuenta a un lector de
         pantalla, porque un icono no tiene texto que leer. */
      var icono = boton.querySelector('i');
      if (icono) {
        icono.className = oculta ? 'bi bi-eye-slash' : 'bi bi-eye';
      }
      campo.focus();
    });
  }

  /* Un doble clic en «CONSULTAR» mandaba dos veces el formulario, y cada
     envio cuenta como un intento contra el limite por IP: dos clics nerviosos
     gastaban dos de los ocho que tiene el cliente. */
  function evitarEnvioDoble() {
    var formulario = document.querySelector('form[method="post"]');
    if (!formulario) {
      return;
    }

    formulario.addEventListener('submit', function () {
      var boton = formulario.querySelector('button[type="submit"]');
      if (boton) {
        boton.disabled = true;
        boton.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2"></span>Consultando…';
      }
    });
  }

  /* Deja escribir la cedula con puntos --que es como esta en la cedula-- sin
     que llegue asi al servidor. El servidor la normaliza igualmente; esto
     solo evita la duda de si hay que quitarlos. */
  function soloDigitos() {
    var campo = document.getElementById('consulta');
    if (!campo) {
      return;
    }

    campo.addEventListener('blur', function () {
      campo.value = campo.value.replace(/\D/g, '');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    conmutarClave();
    evitarEnvioDoble();
    soloDigitos();
  });
})();

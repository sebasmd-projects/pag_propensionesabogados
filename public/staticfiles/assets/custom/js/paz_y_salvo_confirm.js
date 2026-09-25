/*
 * La confirmacion antes de autorizar o retirar un paz y salvo.
 *
 * Antes era un boton que enviaba el formulario al pulsarlo. Un dedo torcido
 * ahi no es un dato mal escrito que se corrige: un paz y salvo autorizado por
 * error es un documento que el cliente descarga y presenta, y retirarlo
 * despues no deshace lo que ya se llevo. Al reves tampoco sale gratis:
 * retirarle el suyo a quien esta al dia le deja sin un papel que suele
 * necesitar para una fecha.
 *
 * Es un dialogo y no un `confirm()` del navegador por dos razones. La
 * primera, que `confirm()` no cabe el nombre del cliente y el asunto con
 * formato, y sin eso un «¿seguro?» solo pregunta si quieres pulsar el boton
 * que acabas de pulsar. La segunda, que el boton que confirma tiene que
 * decir que hace --«Sí, autorizar»-- y no «Aceptar».
 *
 * Si esto no corre, el boton no envia nada. Es a proposito: entre no poder
 * cambiarlo y cambiarlo sin querer, lo segundo es lo caro.
 */
(() => {
  const fuente = document.getElementById('ps-textos');
  const dialogo = document.getElementById('confirmarPazYSalvo');
  if (!fuente || !dialogo || typeof bootstrap === 'undefined') return;

  const textos = JSON.parse(fuente.textContent);
  const modal = new bootstrap.Modal(dialogo);
  const en = selector => dialogo.querySelector(selector);
  const formulario = en('[data-ps-form]');
  const enviar = en('[data-ps-submit]');

  document.querySelectorAll('[data-ps-toggle]').forEach(boton => {
    boton.addEventListener('click', () => {
      // Se autoriza lo que esta retirado y se retira lo que esta autorizado:
      // el boton dice el estado actual, no la accion.
      const texto = textos[boton.dataset.psAuthorized === '1' ? 'retirar' : 'autorizar'];

      en('[data-ps-title]').textContent = texto.titulo;
      en('[data-ps-explicacion]').textContent = texto.explicacion;
      en('[data-ps-nombre]').textContent = boton.dataset.psClient || '';
      en('[data-ps-asunto]').textContent = boton.dataset.psCase || '';

      formulario.action = boton.dataset.psAction;
      enviar.textContent = texto.boton;
      enviar.className = 'btn ' + texto.clase;

      modal.show();
    });
  });
})();

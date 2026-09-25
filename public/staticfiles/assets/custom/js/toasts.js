/*
 * Los avisos flotantes: los de exito se van solos, los de error se quedan.
 *
 * El HTML ya los pinta con `show`, asi que sin esto se ven igual --solo que
 * sin cerrarse--. Por eso se pintan asi y no ocultos: un aviso que depende de
 * que cargue un guion para verse es un aviso que a veces no existe.
 */
(() => {
  if (typeof bootstrap === 'undefined') return;
  document.querySelectorAll('.avisos-flotantes .toast').forEach(aviso => {
    // `getOrCreateInstance` lee el `data-bs-autohide` y el `data-bs-delay` del
    // propio elemento, que es donde la plantilla decidio cuales se quedan.
    bootstrap.Toast.getOrCreateInstance(aviso).show();
  });
})();

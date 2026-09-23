/*
 * El ojo que ensena y esconde la contrasena.
 *
 * Los pasos del codigo y del segundo factor no traen campo de contrasena, asi
 * que aqui no hay nada que ensenar ni esconder. Sin la salida temprana, el
 * `addEventListener` sobre `null` revienta el fichero entero en esas
 * pantallas --y entonces deja de funcionar todo lo que venga despues--.
 */
document.addEventListener("DOMContentLoaded", () => {
  const campo = document.getElementById("id_auth-password");
  const boton = document.getElementById("togglePassword");
  const icono = document.getElementById("togglePasswordIcon");

  if (!campo || !boton || !icono) {
    return;
  }

  boton.addEventListener("click", () => {
    const oculta = campo.type === "password";

    campo.type = oculta ? "text" : "password";
    boton.setAttribute("aria-pressed", String(oculta));

    icono.classList.toggle("bi-eye-slash");
    icono.classList.toggle("bi-eye");
  });
});

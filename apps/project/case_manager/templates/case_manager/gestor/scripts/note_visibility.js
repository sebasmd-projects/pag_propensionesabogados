/* Interruptor de visibilidad de cada nota en «Mi proceso».
   Al cambiarlo se envia el formulario de la nota con fetch (POST, CSRF y la
   cabecera X-Requested-With: fetch) y la pagina no se recarga: solo se
   actualiza la insignia de estado. Si el envio falla, el interruptor vuelve a
   donde estaba y se avisa; sin JavaScript, el boton «Guardar» del <noscript>
   hace el mismo POST y recarga.
   No pasa por el formulario del asunto, asi que no dispara el aviso de
   cambios sin guardar (y el formulario lleva data-unsaved-skip). */
(() => {
  const forms = document.querySelectorAll('form[data-note-visibility]');
  if (!forms.length) return;

  const paint = (form, visible) => {
    const note = form.closest('[data-note]');
    const state = note && note.querySelector('[data-note-state]');
    if (note) note.dataset.noteVisible = visible ? 'true' : 'false';
    if (!state) return;
    state.className = 'badge ' + (visible ? 'text-bg-light' : 'text-bg-secondary');
    state.textContent = '';
    const icon = document.createElement('i');
    icon.className = 'bi me-1 bi-' + (visible ? 'eye' : 'eye-slash');
    state.append(icon, visible ? 'Visible en el portal' : 'Interna');
  };

  forms.forEach(form => {
    const box = form.querySelector('input[name="visible"]');
    const status = form.querySelector('[data-note-status]');
    if (!box) return;

    box.addEventListener('change', async () => {
      const wanted = box.checked;
      const data = new FormData(form);
      // Una casilla sin marcar no viaja en el FormData: se dice a las claras.
      data.set('visible', wanted ? '1' : '0');
      form.classList.add('busy');
      if (status) status.textContent = 'Guardando…';
      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: data,
          headers: {'X-Requested-With': 'fetch'},
          credentials: 'same-origin',
        });
        // Una redireccion (sesion caducada) o un error: no se da por guardado.
        if (!response.ok || response.redirected) throw new Error('no guardado');
        const result = await response.json();
        box.checked = !!result.visible;
        paint(form, !!result.visible);
        if (status) status.textContent = result.visible
          ? 'Ahora la ve el cliente.'
          : 'Ahora es interna.';
      } catch (error) {
        box.checked = !wanted;
        if (status) status.textContent = 'No se pudo guardar. Recargue la página e inténtelo de nuevo.';
      } finally {
        form.classList.remove('busy');
      }
    });
  });
})();

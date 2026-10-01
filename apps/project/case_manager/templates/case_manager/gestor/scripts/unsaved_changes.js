/* Aviso de cambios sin guardar en el formulario del asunto. */
(() => {
  const form = document.querySelector('form[data-unsaved-guard]');
  const modalBox = document.getElementById('cambiosSinGuardar');
  if (!form || !modalBox) return;

  // Estado serializado: campos con nombre y también los del historial de pagos, que no lo tienen.
  const snapshot = () => JSON.stringify([...form.elements]
    .filter(el => /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName)
      && !el.hasAttribute('data-money-display') && el.name !== 'csrfmiddlewaretoken' && el.type !== 'submit')
    .map((el, index) => [el.name || '#' + index,
      el.type === 'checkbox' || el.type === 'radio' ? el.checked : el.value]));

  let initial = null, bypass = false, pending = null, sentinel = false;
  const isDirty = () => initial !== null && !bypass && snapshot() !== initial;

  const modal = window.bootstrap?.Modal ? window.bootstrap.Modal.getOrCreateInstance(modalBox) : null;
  const open = action => {
    pending = action;
    if (modal) modal.show();
    else { modalBox.classList.add('show'); modalBox.style.display = 'block'; }
  };
  const close = () => {
    if (modal) modal.hide();
    else { modalBox.classList.remove('show'); modalBox.style.display = 'none'; }
  };

  const guard = (event, action) => {
    if (!isDirty()) return false;
    event.preventDefault();
    event.stopImmediatePropagation();
    open(action);
    return true;
  };

  form.addEventListener('submit', () => { bypass = true; });

  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button > 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest?.('a[href]');
    if (!link || link.hasAttribute('download') || link.hasAttribute('data-unsaved-skip')
      || link.hasAttribute('data-bs-toggle') || (link.target && link.target !== '_self')) return;
    const href = link.getAttribute('href');
    if (!href || href.startsWith('#') || /^(javascript|mailto|tel):/i.test(href)) return;
    guard(event, () => { location.href = link.href; });
  }, true);

  // Formularios ajenos (p. ej. la nota) también sacan de la página.
  document.addEventListener('submit', event => {
    if (event.target === form || event.target.hasAttribute?.('data-unsaved-skip')) return;
    guard(event, () => event.target.submit());
  }, true);

  window.addEventListener('beforeunload', event => {
    if (!isDirty()) return;
    event.preventDefault();
    event.returnValue = '';
  });

  // Botón «atrás»: al haber cambios se deja una entrada centinela para poder interceptarlo.
  const armSentinel = () => {
    if (sentinel || !isDirty()) return;
    sentinel = true;
    history.pushState({gestorUnsaved: true}, '');
  };
  form.addEventListener('input', armSentinel);
  form.addEventListener('change', armSentinel);
  window.addEventListener('popstate', () => {
    if (!sentinel || bypass) return;
    if (isDirty()) {
      history.pushState({gestorUnsaved: true}, '');
      open(() => history.go(-2));
    } else {
      sentinel = false;
      history.back();
    }
  });

  modalBox.querySelector('[data-unsaved-continue]').addEventListener('click', () => {
    bypass = true;
    const action = pending;
    pending = null;
    close();
    if (action) action();
  });
  modalBox.querySelector('[data-unsaved-save]').addEventListener('click', () => {
    pending = null;
    close();
    if (form.requestSubmit) form.requestSubmit(); else form.dispatchEvent(new Event('submit', {cancelable: true})) && form.submit();
  });
  modalBox.addEventListener('hidden.bs.modal', () => { pending = null; });
  modalBox.querySelectorAll('[data-unsaved-cancel]').forEach(button => button.addEventListener('click', () => {
    pending = null;
    close();
  }));

  // Se toma la foto inicial cuando los demás guiones ya han normalizado los campos.
  const take = () => setTimeout(() => { initial = snapshot(); }, 0);
  if (document.readyState === 'complete') take(); else window.addEventListener('load', take, {once: true});
})();

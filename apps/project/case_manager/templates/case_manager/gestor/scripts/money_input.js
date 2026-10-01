/* Importes en pesos colombianos: "$ 1.234.567" solo a la vista.
 *
 * El campo real (con su name) pasa a ser oculto y conserva SIEMPRE el número
 * limpio; el que escribe el usuario es un espejo sin name. Así el servidor
 * recibe lo mismo que antes y la validación no cambia. */
(() => {
  const MAX_DIGITS = 13;
  const digits = value => String(value ?? '').replace(/\D/g, '');
  // Un valor que viene del campo real puede traer decimales ("1500.00"): no son miles.
  const clean = value => digits(String(value ?? '').split(/[.,]\d*$/)[0]).slice(0, MAX_DIGITS);
  const format = raw => {
    const number = String(raw).replace(/^0+(?=\d)/, '');
    return number ? '$ ' + number.replace(/\B(?=(\d{3})+(?!\d))/g, '.') : '';
  };

  const attach = original => {
    if (!original || original.dataset.moneyAttached) return;
    original.dataset.moneyAttached = 'true';
    const view = original.ownerDocument.defaultView;
    const native = Object.getOwnPropertyDescriptor(view.HTMLInputElement.prototype, 'value');

    const display = original.ownerDocument.createElement('input');
    display.type = 'text';
    display.inputMode = 'numeric';
    display.autocomplete = 'off';
    display.placeholder = '$ 0';
    display.className = original.className;
    display.setAttribute('data-money-display', '');
    display.disabled = original.disabled;

    const labelFor = original.id && original.ownerDocument.querySelector(`label[for="${original.id}"]`);
    if (original.id) display.id = original.id + '_display';
    if (labelFor) {
      if (!labelFor.id) labelFor.id = original.id + '_label';
      display.setAttribute('aria-labelledby', labelFor.id);
      labelFor.addEventListener('click', event => {
        if (event.target === labelFor) display.focus();
      });
    }

    const refresh = () => { display.value = format(clean(native.get.call(original))); };
    const write = raw => native.set.call(original, raw);

    Object.defineProperty(original, 'value', {
      configurable: true,
      get() { return native.get.call(this); },
      set(next) { native.set.call(this, next == null ? '' : String(next)); refresh(); },
    });

    original.type = 'hidden';
    original.before(display);
    refresh();

    display.addEventListener('input', () => {
      const caret = display.selectionStart ?? display.value.length;
      const before = digits(display.value.slice(0, caret)).length;
      const raw = digits(display.value).slice(0, MAX_DIGITS).replace(/^0+(?=\d)/, '');
      write(raw);
      display.value = format(raw);
      // El cursor se queda tras el mismo número de cifras, no en la misma posición.
      let seen = 0, position = display.value.length;
      if (before === 0) position = raw ? 2 : 0;
      else for (let i = 0; i < display.value.length; i++) {
        if (/\d/.test(display.value[i]) && ++seen === before) { position = i + 1; break; }
      }
      display.setSelectionRange?.(position, position);
      original.dispatchEvent(new view.Event('input'));
    });
    display.addEventListener('change', () => original.dispatchEvent(new view.Event('change')));
    display.addEventListener('blur', refresh);
    display.addEventListener('copy', event => {
      if (display.selectionStart === display.selectionEnd || !event.clipboardData) return;
      event.clipboardData.setData('text/plain', digits(display.value.slice(display.selectionStart, display.selectionEnd)));
      event.preventDefault();
    });

    new view.MutationObserver(() => {
      display.disabled = original.disabled;
      display.classList.toggle('is-invalid', original.classList.contains('is-invalid'));
    }).observe(original, {attributes: true, attributeFilter: ['disabled', 'class']});
  };

  const scan = root => root.querySelectorAll?.('input[data-money]').forEach(attach);
  window.gestorMoney = {attach, format, clean};
  scan(document);
  // Los pagos nuevos se clonan de una plantilla y llegan después.
  new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
    if (node.nodeType === 1) { if (node.matches('input[data-money]')) attach(node); scan(node); }
  }))).observe(document.body, {childList: true, subtree: true});
})();

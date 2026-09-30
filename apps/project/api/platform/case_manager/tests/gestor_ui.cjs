// Formato COP, aviso de cambios sin guardar y fechas de pagos, con los guiones reales.
// Requiere jsdom y el HTML de edicion exportado por test_dynamic_flow:
//   CASE_FLOW_HTML_DIR=<dir> python manage.py test ...tests.test_dynamic_flow
//   node gestor_ui.cjs <dir>
// (el mismo directorio trae dashboard.html si se ejecuta test_gestor: filtros y tooltip)
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync(path.join(process.argv[2], 'edit.html'), 'utf8');

function boot() {
  const dom = new JSDOM(html, {runScripts: 'outside-only', pretendToBeVisual: true, url: 'http://localhost/gestor/asuntos/1/'});
  const w = dom.window;
  w.HTMLFormElement.prototype.requestSubmit = function () {
    const event = new w.Event('submit', {bubbles: true, cancelable: true});
    this.dispatchEvent(event);
    this.submitted = (this.submitted || 0) + 1;
  };
  w.HTMLFormElement.prototype.submit = function () { this.submitted = (this.submitted || 0) + 1; };
  const wanted = ['const source =', 'Importes en pesos', 'Gestión de Pagos se inicializa', 'Aviso de cambios'];
  for (const script of w.document.querySelectorAll('script:not([src])')) {
    if (wanted.some(text => script.textContent.includes(text))) w.eval(script.textContent);
  }
  return w;
}
const tick = (w, ms = 5) => new Promise(resolve => w.setTimeout(resolve, ms));
const type = (w, input, text) => {
  // Escribe carácter a carácter, como el navegador.
  for (const char of text) {
    const start = input.selectionStart, end = input.selectionEnd;
    input.value = input.value.slice(0, start) + char + input.value.slice(end);
    input.setSelectionRange(start + 1, start + 1);
    input.dispatchEvent(new w.Event('input', {bubbles: true}));
  }
};

(async () => {
  // ---- Formato monetario ----
  let w = boot();
  const doc = w.document;
  const original = doc.getElementById('id_finance-0-agreed_fee');
  const display = doc.getElementById('id_finance-0-agreed_fee_display');
  assert(display, 'debe existir el campo visible');
  assert.equal(original.type, 'hidden');
  assert.equal(original.name, 'finance-0-agreed_fee');
  assert.equal(display.name, '');
  type(w, display, '1234567');
  assert.equal(display.value, '$ 1.234.567');
  assert.equal(original.value, '1234567');
  // Escribir en medio no manda el cursor al final.
  display.setSelectionRange(4, 4); // "$ 1.|234.567"
  type(w, display, '9');
  assert.equal(display.value, '$ 19.234.567');
  assert.equal(display.selectionStart, 4);
  assert.equal(original.value, '19234567');
  // Letras y signos no entran; sin decimales.
  type(w, display, 'a,.-');
  assert.equal(original.value, '19234567');
  // Asignaciones por código (payment_form) se reflejan en la vista.
  original.value = '0';
  assert.equal(display.value, '$ 0');
  original.value = '';
  assert.equal(display.value, '');
  // Copiar entrega el número limpio.
  display.value = '$ 1.234.567';
  display.setSelectionRange(0, display.value.length);
  const copied = {};
  const copy = new w.Event('copy', {bubbles: true, cancelable: true});
  copy.clipboardData = {setData: (kind, value) => { copied[kind] = value; }};
  display.dispatchEvent(copy);
  assert.equal(copied['text/plain'], '1234567');
  assert(copy.defaultPrevented);
  // El formulario envía el número limpio y no envía el campo visible.
  original.value = '2500000';
  const data = new w.FormData(doc.querySelector('form[data-unsaved-guard]'));
  assert.equal(data.get('finance-0-agreed_fee'), '2500000');
  assert(![...data.keys()].some(key => key.endsWith('_display')));

  // Los pagos añadidos también se formatean, con el valor limpio en el oculto.
  const mandate = doc.getElementById('id_finance-0-mandate');
  mandate.value = 'Modalidad de pago';
  mandate.dispatchEvent(new w.Event('change', {bubbles: true}));
  doc.querySelector('[data-add-payment]').click();
  await tick(w);
  const row = doc.querySelector('[data-payment-row]');
  const rowDisplay = row.querySelector('[data-money-display]');
  const rowValue = row.querySelector('[data-payment-amount]');
  assert(rowDisplay, 'el pago nuevo debe tener campo visible');
  type(w, rowDisplay, '450000');
  assert.equal(rowDisplay.value, '$ 450.000');
  assert.equal(rowValue.value, '450000');
  const history = JSON.parse(doc.getElementById('id_finance-0-payment_history').value);
  assert.equal(history[0].amount, 450000);

  // ---- Fechas: no se tocan mientras se escriben ----
  const nextDate = row.querySelector('[data-payment-next-date]');
  const payDate = row.querySelector('[data-payment-date]');
  assert.equal(nextDate.closest('[data-money-display]'), null);
  assert(!nextDate.hasAttribute('data-money'));
  payDate.value = '2026-09-01';
  payDate.dispatchEvent(new w.Event('change', {bubbles: true}));
  let minWrites = 0;
  const observer = new w.MutationObserver(records => { minWrites += records.filter(r => r.attributeName === 'min').length; });
  observer.observe(nextDate, {attributes: true});
  // El navegador entrega el valor a cada pulsación válida del año: 0002, 0020, 0202, 2027.
  for (const year of ['0002', '0020', '0202', '2027']) {
    nextDate.value = `${year}-01-30`;
    nextDate.dispatchEvent(new w.Event('input', {bubbles: true}));
  }
  await tick(w);
  assert.equal(nextDate.value, '2027-01-30');
  assert.equal(minWrites, 0, 'no se reescribe min mientras se teclea');
  nextDate.dispatchEvent(new w.Event('change', {bubbles: true}));
  assert.equal(nextDate.value, '2027-01-30');
  assert.equal(JSON.parse(doc.getElementById('id_finance-0-payment_history').value)[0].next_date, '2027-01-30');

  // ---- Cambios sin guardar ----
  w = boot();
  const d = w.document;
  await tick(w, 20);
  w.dispatchEvent(new w.Event('load'));
  await tick(w, 20);
  const modal = d.getElementById('cambiosSinGuardar');
  const form = d.querySelector('form[data-unsaved-guard]');
  const link = d.querySelector('a.nav-link[href]');
  const click = target => {
    const event = new w.MouseEvent('click', {bubbles: true, cancelable: true, button: 0});
    target.dispatchEvent(event);
    return event;
  };
  const opened = () => modal.classList.contains('show');
  // Sin cambios: el enlace sigue y no hay aviso.
  assert(!click(link).defaultPrevented);
  assert(!opened());
  // Con cambios: aviso y enlace detenido.
  const number = d.getElementById('id_case_number');
  number.value = 'X-1';
  number.dispatchEvent(new w.Event('input', {bubbles: true}));
  assert(click(link).defaultPrevented);
  assert(opened());
  // beforeunload pide confirmación mientras hay cambios.
  const unload = new w.Event('beforeunload', {cancelable: true});
  w.dispatchEvent(unload);
  assert(unload.defaultPrevented);
  // Guardar cambios envía el formulario y cierra el aviso.
  d.querySelector('[data-unsaved-save]').click();
  assert(!opened());
  assert.equal(form.submitted, 1);
  // Tras enviar, ya no vuelve a saltar ni al salir.
  assert(!click(link).defaultPrevented);
  const unload2 = new w.Event('beforeunload', {cancelable: true});
  w.dispatchEvent(unload2);
  assert(!unload2.defaultPrevented);

  // Continuar descarta y sigue con la acción.
  w = boot();
  await tick(w, 20);
  w.dispatchEvent(new w.Event('load'));
  await tick(w, 20);
  const d2 = w.document;
  const n2 = d2.getElementById('id_case_number');
  n2.value = 'Y-2';
  n2.dispatchEvent(new w.Event('input', {bubbles: true}));
  const second = d2.querySelector('a.nav-link[href]');
  const ev = new w.MouseEvent('click', {bubbles: true, cancelable: true, button: 0});
  second.dispatchEvent(ev);
  assert(ev.defaultPrevented);
  d2.querySelector('[data-unsaved-continue]').click();
  assert(!d2.getElementById('cambiosSinGuardar').classList.contains('show'));
  // Revertir el cambio devuelve el estado limpio.
  w = boot();
  await tick(w, 20);
  w.dispatchEvent(new w.Event('load'));
  await tick(w, 20);
  const n3 = w.document.getElementById('id_case_number');
  const before = n3.value;
  n3.value = 'Z';
  n3.value = before;
  const ev3 = new w.MouseEvent('click', {bubbles: true, cancelable: true, button: 0});
  w.document.querySelector('a.nav-link[href]').dispatchEvent(ev3);
  assert(!ev3.defaultPrevented);


  // ---- Comparativo del panel: filtros independientes y tooltip ----
  const dashFile = path.join(process.argv[2], 'dashboard.html');
  if (fs.existsSync(dashFile)) {
    const dash = new JSDOM(fs.readFileSync(dashFile, 'utf8'), {runScripts: 'outside-only', pretendToBeVisual: true, url: 'http://localhost/gestor/'});
    const dw = dash.window, dd = dw.document;
    for (const script of dd.querySelectorAll('script:not([src])')) {
      if (script.textContent.includes('data-financial-chart')) dw.eval(script.textContent);
    }
    const chips = [...dd.querySelectorAll('[data-series-toggle]')];
    const rows = [...dd.querySelectorAll('[data-pie-toggle]')];
    const bar = (key) => [...dd.querySelectorAll('.gestor-time-bar[data-series="' + key + '"]')];
    const shares = () => rows.map(r => Number(r.querySelector('[data-pie-share]').textContent));
    const pieFill = () => dd.querySelector('[data-financial-pie]').style.getPropertyValue('--pie-fill');
    const axisLabels = () => [...dd.querySelectorAll('[data-chart-axis] span')].map(x => x.textContent);
    const tip = dd.querySelector('[data-chart-tooltip]');
    assert.equal(chips.length, 5);
    assert.equal(rows.length, 5);
    // Accesibles con teclado: casillas y botones reales.
    assert(chips.every(c => c.type === 'checkbox'));
    assert(rows.every(r => r.tagName === 'BUTTON' && r.type === 'button'));
    assert(rows.every(r => r.getAttribute('aria-pressed') === 'true'));
    assert.equal(shares().reduce((a, b) => a + b, 0), 100);
    assert(axisLabels().length >= 3 && axisLabels()[0] === '$0 M', 'eje Y abreviado');
    const pieBefore = pieFill(), sharesBefore = shares(), axisBefore = axisLabels().join('|');

    // Chip de las barras: oculta solo las barras; la torta queda igual.
    const chip = key => chips.find(c => c.dataset.seriesToggle === key);
    chip('expectation').checked = false;
    chip('expectation').dispatchEvent(new dw.Event('change', {bubbles: true}));
    assert(bar('expectation').every(b => b.hidden));
    assert(bar('paid').every(b => !b.hidden));
    assert.deepEqual(shares(), sharesBefore);
    assert.equal(pieFill(), pieBefore);
    assert(rows.every(r => r.getAttribute('aria-pressed') === 'true'));
    assert.notEqual(axisLabels().join('|'), axisBefore, 'la escala se recalcula con lo visible');
    chip('expectation').checked = true;
    chip('expectation').dispatchEvent(new dw.Event('change', {bubbles: true}));
    assert(bar('expectation').every(b => !b.hidden));

    // Fila de la torta: oculta solo su sector y recalcula porcentajes.
    const row = key => rows.find(r => r.dataset.pieToggle === key);
    row('expectation').click();
    assert.equal(row('expectation').getAttribute('aria-pressed'), 'false');
    assert(row('expectation').closest('[data-pie-item]').classList.contains('is-off'));
    assert.equal(Number(row('expectation').querySelector('[data-pie-share]').textContent), 0);
    const after = shares();
    assert.equal(after.reduce((a, b) => a + b, 0), 100);
    assert(after[0] > sharesBefore[0], 'los demás porcentajes suben');
    assert.notEqual(pieFill(), pieBefore);
    assert(bar('expectation').every(b => !b.hidden), 'las barras no cambian');
    assert(chips.every(c => c.checked));
    // Se puede volver a activar (la fila sigue visible).
    row('expectation').click();
    assert.equal(row('expectation').getAttribute('aria-pressed'), 'true');
    assert.deepEqual(shares(), sharesBefore);
    // Sin sectores visibles aparece el aviso.
    rows.forEach(r => r.click());
    assert.equal(dd.querySelector('[data-pie-empty]').hidden, false);
    rows.forEach(r => r.click());
    assert.equal(dd.querySelector('[data-pie-empty]').hidden, true);

    // Tooltip: periodo y valor de cada serie visible, en formato COP.
    const bucket = [...dd.querySelectorAll('[data-bucket]')].find(b => b.querySelector('.gestor-time-bar[data-series="agreed"]').dataset.value === '5000000');
    assert(bucket, 'hay un grupo con lo pactado');
    assert(tip.hidden);
    bucket.dispatchEvent(new dw.MouseEvent('mouseenter', {bubbles: false, clientX: 10, clientY: 10}));
    assert(!tip.hidden);
    assert.equal(tip.querySelector('b').textContent, bucket.dataset.title);
    assert(tip.textContent.includes('Pactado: $ 5.000.000'), tip.textContent);
    assert.equal(tip.querySelectorAll('div').length, 5);
    // Respeta el filtro de barras.
    chip('paid').checked = false;
    chip('paid').dispatchEvent(new dw.Event('change', {bubbles: true}));
    bucket.dispatchEvent(new dw.MouseEvent('mouseenter', {bubbles: false}));
    assert(!tip.textContent.includes('Pagado'));
    assert.equal(tip.querySelectorAll('div').length, 4);
    // Salir, tocar (abre y cierra con otro toque), foco de teclado y Escape.
    bucket.dispatchEvent(new dw.MouseEvent('mouseleave'));
    assert(tip.hidden);
    bucket.click();
    assert(!tip.hidden);
    bucket.click();
    assert(tip.hidden);
    bucket.focus();
    assert(!tip.hidden, 'el foco de teclado también lo muestra');
    dd.dispatchEvent(new dw.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    assert(tip.hidden);
    bucket.click();
    dd.body.click();
    assert(tip.hidden, 'tocar fuera lo cierra');
  }

  console.log('Formato COP, copia limpia, fechas sin truncar, aviso de cambios, filtros independientes y tooltip verificados.');
})().catch(error => { console.error(error); process.exit(1); });

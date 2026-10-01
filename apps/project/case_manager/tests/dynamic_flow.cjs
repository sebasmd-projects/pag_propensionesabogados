// Requiere jsdom y el HTML sintético exportado por test_dynamic_flow.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const reference = require('./fixtures/reference_flow.json');
const directory = process.argv[2];
function load(name) {
  const dom = new JSDOM(fs.readFileSync(path.join(directory, name + '.html'), 'utf8'), {runScripts: 'outside-only'});
  const w = dom.window;
  const field = name => w.document.getElementById('id_' + name);
  const visible = name => {
    const box = field(name).closest('[data-field-for]');
    return !box.hidden && !box.classList.contains('d-none');
  };
  const start = () => {
    for (const script of w.document.querySelectorAll('script:not([src])')) {
      if (script.textContent.includes('const source =') || script.textContent.includes('Gestión de Pagos se inicializa')) w.eval(script.textContent);
    }
  };
  const change = (name, value) => {
    field(name).value = value;
    field(name).dispatchEvent(new w.Event('change', {bubbles: true}));
  };
  return {w, field, visible, start, change};
}
const fresh = load('create');
for (const name of ['subtype', 'second_subtype', 'instance', 'court', 'service_other']) {
  assert.equal(fresh.visible(name), false, `Sin JS: ${name} debe estar oculto`);
}
fresh.start();
const options = field => [...field.options].map(o => o.value).filter(v => v && v !== 'Otro').sort();
let paths = 0;
for (const [service, branches] of Object.entries(reference.services)) {
  fresh.change('service', service);
  assert.deepEqual(options(fresh.field('subtype')), Object.keys(branches).sort());
  assert.equal(fresh.visible('second_subtype'), false);
  assert.equal(fresh.visible('court'), service === 'Representación judicial');
  assert.deepEqual(options(fresh.field('instance')), [...reference.instances[service]].sort());
  for (const [parent, processes] of Object.entries(branches)) {
    fresh.change('subtype', parent);
    assert.equal(fresh.visible('second_subtype'), processes.length > 0);
    assert.deepEqual(options(fresh.field('second_subtype')), [...processes].sort());
    for (const process of processes) {
      fresh.change('second_subtype', process);
      assert.equal(fresh.field('subtype').value, parent);
      assert.equal(fresh.field('second_subtype').value, process);
      paths++;
    }
  }
}
fresh.change('service', 'Representación judicial');
fresh.change('subtype', 'Contencioso administrativo');
fresh.change('second_subtype', 'Nulidad y restablecimiento del derecho');
fresh.change('subtype', 'Laboral');
assert.equal(fresh.field('second_subtype').value, '');
assert(!options(fresh.field('second_subtype')).includes('Nulidad y restablecimiento del derecho'));
fresh.change('subtype', 'Otro');
assert(fresh.visible('subtype_other'));
assert(!fresh.visible('second_subtype'));
fresh.change('service', 'Otro');
assert(fresh.visible('service_other'));
assert(!fresh.visible('subtype'));
assert(!fresh.visible('subtype_other'));
fresh.change('service', 'Consultoría');
fresh.change('instance', 'Finalizada');
fresh.change('service', 'Conciliación');
assert.equal(fresh.field('instance').value, 'Finalizada');
fresh.change('service', 'Representación judicial');
assert.equal(fresh.field('instance').value, '');
const edit = load('edit');
for (const initialize of [false, true]) {
  if (initialize) edit.start();
  assert.equal(edit.field('service').value, 'Representación judicial');
  assert.equal(edit.field('subtype').value, 'Contencioso administrativo');
  assert.equal(edit.field('second_subtype').value, 'Nulidad y restablecimiento del derecho');
  assert(edit.visible('second_subtype'));
}
console.log(`${paths} tipos de proceso verificados; carga inicial, cambios de rama, Otro y edición verificados.`);

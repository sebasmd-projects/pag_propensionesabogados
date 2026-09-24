/* Flujo del HTML de referencia: servicio -> área/subnivel -> proceso. */
(() => {
  const source = document.getElementById('case-classification');
  if (!source) return;
  const catalog = JSON.parse(source.textContent);
  const field = name => document.getElementById(`id_${name}`);
  const column = input => input.closest('[data-field-for]');
  const show = (box, visible) => {
    box.hidden = !visible;
    box.classList.toggle('d-none', !visible);
  };
  const service = field('service'), subtype = field('subtype');
  const originalService = service.value;
  const refill = (name, values) => {
    const select = field(name);
    select.replaceChildren(new Option('---------', ''), ...values.map(v => new Option(v, v)));
    show(column(select), values.length > 0);
  };
  const updateOthers = () => {
    ['service', 'subtype', 'second_subtype'].forEach(name => {
      const input = field(`${name}_other`), parent = field(name);
      const visible = !column(parent).hidden && /^(otro|otra)/i.test(parent.value);
      show(column(input), visible);
      input.required = visible;
    });
  };
  const details = () => {
    const judicial = service.value === 'Representación judicial';
    document.querySelector(`label[for="${subtype.id}"]`).textContent = judicial ? 'Área' : 'Subnivel';
    document.getElementById('case-details-title').textContent = judicial ? 'Representación judicial' : 'Datos del proceso';
    show(column(field('court')), judicial);
    document.querySelectorAll('[data-procedure-block]').forEach(block => {
      const type = block.dataset.procedureBlock;
      show(block, type === 'general' || (service.value === originalService && field('procedure').value === type));
    });
    updateOthers();
  };
  service.addEventListener('change', () => {
    refill('subtype', service.value === 'Otro' ? [] : catalog.subtypes[service.value] || []);
    refill('second_subtype', []);
    refill('instance', catalog.instances[service.value] || []);
    if (service.value !== 'Representación judicial') field('court').value = '';
    details();
  });
  subtype.addEventListener('change', () => {
    refill('second_subtype', catalog.seconds[service.value]?.[subtype.value] || []);
    updateOthers();
  });
  field('second_subtype').addEventListener('change', updateOthers);
  ['subtype', 'second_subtype', 'instance'].forEach(name => {
    const input = field(name);
    show(column(input), !!input.value || (input.options.length > 1 && !(name === 'subtype' && service.value === 'Otro')));
  });
  details();

})();

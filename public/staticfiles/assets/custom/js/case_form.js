(() => {
  const source = document.getElementById('case-classification');
  if (!source) return;
  const catalog = JSON.parse(source.textContent);
  const field = name => document.getElementById(`id_${name}`);
  const service = field('service'), area = field('area'), subtype = field('subtype');
  const refill = (name, values) => {
    const select = field(name), previous = select.value;
    select.replaceChildren(new Option('---------', ''), ...values.map(value => new Option(value, value)));
    select.value = values.includes(previous) ? previous : '';
  };
  const updateOthers = () => {
    ['service', 'procedure', 'area', 'subtype', 'second_subtype'].forEach(name => {
      const input = field(`${name}_other`);
      const visible = /^(otro|otra)/i.test(field(name).value);
      input.closest('.col-12').hidden = !visible;
      input.required = visible;
    });
  };
  const updateSecond = () => {
    refill('second_subtype', catalog.seconds[service.value]?.[subtype.value] || ['Otro']);
    updateOthers();
  };
  const updateClassification = () => {
    refill('subtype', catalog.subtypes[service.value]?.[area.value] || ['Otro']);
    refill('instance', catalog.instances[service.value] || []);
    updateSecond();
  };
  service.addEventListener('change', updateClassification);
  area.addEventListener('change', updateClassification);
  subtype.addEventListener('change', updateSecond);
  ['procedure', 'second_subtype'].forEach(name => field(name).addEventListener('change', updateOthers));
  // No reconstruir al abrir: las opciones del servidor conservan valores historicos.
  updateOthers();
  // Abrir bloques con datos o errores, incluso si el exportado no tiene tramite.
  ['bloqueJudicial', 'bloqueAdministrativo', 'bloquePolicivo'].forEach(id => {
    const block = document.getElementById(id);
    if (Array.from(block.querySelectorAll('input, select')).some(input => input.value || input.classList.contains('is-invalid'))) {
      block.classList.add('show');
      const button = document.querySelector(`[data-bs-target="#${id}"]`);
      button.classList.remove('collapsed');
      button.setAttribute('aria-expanded', 'true');
    }
  });
})();

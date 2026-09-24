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

  document.querySelectorAll('select[name$="-mandate"]').forEach(mandate => {
    const prefix = mandate.name.slice(0, -'mandate'.length);
    const moneyField = name => document.getElementsByName(prefix + name)[0];
    const percentage = moneyField('contingency_percentage');
    const value = moneyField('contingency_value');
    const summary = mandate.closest('.card-body').querySelector('[data-finance-summary]');
    const currency = n => new Intl.NumberFormat('es-CO', {style: 'currency', currency: 'COP', maximumFractionDigits: 0}).format(n);
    const updateFinance = (changed = false) => {
      const litis = mandate.value === 'Cuota litis';
      const payment = mandate.value === 'Modalidad de pago';
      const fixed = litis && percentage.value === '0';
      const visibility = {contingency_percentage: litis, contingency_value: litis,
        agreed_fee: payment, paid_amount: payment || fixed};
      Object.entries(visibility).forEach(([name, visible]) => {
        const input = moneyField(name);
        // Al cambiar modalidad se eliminan importes que ya no aplican.
        if (changed && !visible) input.value = '0';
        show(column(input), visible || (!changed && input.classList.contains('is-invalid')));
      });
      document.querySelector(`label[for="${value.id}"]`).textContent = fixed ? 'Valor fijo cerrado' : 'Valor esperado / expectativa';
      value.disabled = litis && percentage.value === '';
      const agreed = Number(moneyField(payment ? 'agreed_fee' : 'contingency_value').value || 0);
      const paid = Number(moneyField('paid_amount').value || 0);
      show(summary, payment || litis);
      summary.textContent = payment || fixed
        ? `Pactado: ${currency(agreed)} · Pagado: ${currency(paid)} · Saldo: ${currency(Math.max(0, agreed - paid))}`
        : `Expectativa: ${currency(agreed)}`;
    };
    mandate.addEventListener('change', () => updateFinance(true));
    percentage.addEventListener('change', () => updateFinance(true));
    ['contingency_value', 'agreed_fee', 'paid_amount'].forEach(name => moneyField(name).addEventListener('input', () => updateFinance()));
    updateFinance();
  });
})();

/* Gestión de Pagos se inicializa independientemente de la clasificación. */
(() => {
  const column = input => input.closest('[data-field-for]');
  const show = (box, visible) => {
    if (!box) return;
    box.hidden = !visible;
    box.classList.toggle('d-none', !visible);
  };
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
      const free = ['Ad honorem', 'Curaduría'].includes(mandate.value);
      const fixed = litis && percentage.value === '0';
      const visibility = {contingency_percentage: litis, contingency_value: litis,
        agreed_fee: payment, paid_amount: payment || fixed};
      Object.entries(visibility).forEach(([name, visible]) => {
        const input = moneyField(name);
        // Al cambiar modalidad se eliminan importes que ya no aplican.
        if (free || (changed && !visible)) input.value = '0';
        input.disabled = free;
        show(column(input), !free && (visible || (!changed && input.classList.contains('is-invalid'))));
      });
      document.querySelector(`label[for="${value.id}"]`).textContent = fixed ? 'Valor fijo cerrado' : 'Valor esperado / expectativa';
      value.disabled = free || (litis && percentage.value === '');
      show(column(moneyField('show_in_dashboard')), !free);
      show(mandate.closest('.card').querySelector('[data-contingency-help]'), litis);
      const agreed = Number(moneyField(payment ? 'agreed_fee' : 'contingency_value').value || 0);
      const paid = Number(moneyField('paid_amount').value || 0);
      show(summary, payment || litis || free);
      summary.textContent = free
        ? `${mandate.value}: servicio gratuito. Sin honorarios, pagos ni saldo por cobrar.`
        : payment || fixed
        ? `Pactado: ${currency(agreed)} · Pagado: ${currency(paid)} · Saldo: ${currency(Math.max(0, agreed - paid))}`
        : `Expectativa: ${currency(agreed)}`;
    };
    mandate.addEventListener('change', () => updateFinance(true));
    percentage.addEventListener('change', () => updateFinance(true));
    ['contingency_value', 'agreed_fee', 'paid_amount'].forEach(name => moneyField(name).addEventListener('input', () => updateFinance()));
    updateFinance();
  });
})();

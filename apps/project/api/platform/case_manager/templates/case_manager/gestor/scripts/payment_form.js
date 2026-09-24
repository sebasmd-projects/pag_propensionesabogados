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
    const history = mandate.closest('.card-body').querySelector('[data-payment-history]');
    const rows = history.querySelector('[data-payment-rows]');
    const historyField = moneyField('payment_history');
    const serialize = () => {
      let number = 0;
      const payments = Array.from(rows.querySelectorAll('[data-payment-row]')).map(row => {
        const kind = row.dataset.kind;
        if (kind === 'payment') {
          number += 1;
          row.querySelector('[data-payment-title]').textContent = number === 1 ? 'Pago 1 / primer abono' : `Pago ${number}`;
        }
        const amount = Number(row.querySelector('[data-payment-amount]').value || 0);
        const date = row.querySelector('[data-payment-date]');
        date.required = amount > 0 && row.dataset.legacy !== 'true';
        row.querySelector('[data-payment-next-date]').min = date.value;
        return {kind, amount, date: date.value,
          next_date: row.querySelector('[data-payment-next-date]').value,
          legacy: row.dataset.legacy === 'true'};
      });
      historyField.value = JSON.stringify(payments);
      return payments.reduce((sum, payment) => sum + payment.amount, 0);
    };
    const currency = n => new Intl.NumberFormat('es-CO', {style: 'currency', currency: 'COP', maximumFractionDigits: 0}).format(n);
    const updateFinance = (changed = false) => {
      const litis = mandate.value === 'Cuota litis';
      const payment = mandate.value === 'Modalidad de pago';
      const free = ['Ad honorem', 'Curaduría'].includes(mandate.value);
      const fixed = litis && percentage.value === '0';
      const visibility = {contingency_percentage: litis, contingency_value: litis,
        agreed_fee: payment, paid_amount: fixed};
      Object.entries(visibility).forEach(([name, visible]) => {
        const input = moneyField(name);
        // Al cambiar modalidad se eliminan importes que ya no aplican.
        if (free || (changed && !visible && !(payment && name === 'paid_amount'))) input.value = '0';
        input.disabled = free;
        show(column(input), !free && (visible || (!changed && input.classList.contains('is-invalid'))));
      });
      document.querySelector(`label[for="${value.id}"]`).textContent = fixed ? 'Valor fijo cerrado' : 'Valor esperado / expectativa';
      value.disabled = free || (litis && percentage.value === '');
      show(column(moneyField('show_in_dashboard')), !free);
      show(mandate.closest('.card').querySelector('[data-contingency-help]'), litis);
      show(history, payment);
      history.querySelectorAll('input, button').forEach(input => { input.disabled = !payment; });
      if (payment) moneyField('paid_amount').value = serialize();
      const agreed = Number(moneyField(payment ? 'agreed_fee' : 'contingency_value').value || 0);
      const paid = Number(moneyField('paid_amount').value || 0);
      show(summary, payment || litis || free);
      summary.textContent = free
        ? `${mandate.value}: servicio gratuito. Sin honorarios, pagos ni saldo por cobrar.`
        : payment || fixed
        ? `Total del contrato: ${currency(agreed)} · Total pagado: ${currency(paid)} · Saldo pendiente: ${currency(Math.max(0, agreed - paid))}`
        : `Expectativa: ${currency(agreed)}`;
    };
    mandate.addEventListener('change', () => updateFinance(true));
    percentage.addEventListener('change', () => updateFinance(true));
    ['contingency_value', 'agreed_fee', 'paid_amount'].forEach(name => moneyField(name).addEventListener('input', () => updateFinance()));
    history.querySelector('[data-add-payment]').addEventListener('click', () => {
      if (rows.children.length >= 100) return;
      const row = history.querySelector('template').content.firstElementChild.cloneNode(true);
      row.dataset.kind = 'payment';
      rows.append(row);
      updateFinance();
      row.querySelector('input').focus();
    });
    rows.addEventListener('input', () => updateFinance());
    rows.addEventListener('change', () => updateFinance());
    rows.addEventListener('click', event => {
      const button = event.target.closest('[data-remove-payment]');
      if (!button) return;
      const row = button.closest('[data-payment-row]');
      if (row.dataset.kind === 'payment') row.remove();
      updateFinance();
    });
    mandate.form.addEventListener('submit', () => { if (mandate.value === 'Modalidad de pago') serialize(); });
    updateFinance();
  });
})();

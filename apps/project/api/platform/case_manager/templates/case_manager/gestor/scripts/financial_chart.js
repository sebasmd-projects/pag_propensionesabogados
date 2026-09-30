/* Filtros por serie del comparativo: barras y torta comparten el estado. */
(() => {
  const root = document.querySelector('[data-financial-chart]');
  if (!root) return;
  const toggles = [...root.querySelectorAll('[data-series-toggle]')];
  const bars = [...root.querySelectorAll('.gestor-time-bar[data-series]')];
  const pie = root.querySelector('[data-financial-pie]');
  const items = [...root.querySelectorAll('[data-pie-item]')];
  const empty = root.querySelector('[data-pie-empty]');
  const active = () => new Set(toggles.filter(t => t.checked).map(t => t.dataset.seriesToggle));
  const color = tone => getComputedStyle(document.documentElement).getPropertyValue('--bs-' + tone).trim() || '#888';
  const money = n => new Intl.NumberFormat('es-CO', {maximumFractionDigits: 0}).format(n);

  const render = () => {
    const on = active();
    let max = 0;
    bars.forEach(bar => {
      const visible = on.has(bar.dataset.series);
      bar.hidden = !visible;
      if (visible) max = Math.max(max, Number(bar.dataset.value));
    });
    // La escala se recalcula con lo visible: ocultar la serie mayor no deja las demás aplastadas.
    bars.forEach(bar => {
      const value = Number(bar.dataset.value);
      const height = value && max ? Math.round(value * 100 / max) : 0;
      bar.style.setProperty('--bar-height', height + '%');
      bar.classList.toggle('is-zero', !value);
    });

    const shown = items.filter(item => on.has(item.dataset.pieItem));
    const total = shown.reduce((sum, item) => sum + Number(item.dataset.value), 0);
    items.forEach(item => {
      const visible = on.has(item.dataset.pieItem);
      item.hidden = !visible;
      const share = visible && total ? Math.round(Number(item.dataset.value) * 100 / total) : 0;
      item.querySelector('[data-pie-share]').textContent = share;
    });
    let cursor = 0;
    const stops = [];
    shown.forEach(item => {
      const value = Number(item.dataset.value);
      if (!value) return;
      const end = cursor + value * 100 / total;
      stops.push(`${color(item.dataset.tone)} ${cursor}% ${end}%`);
      cursor = end;
    });
    pie.style.setProperty('--pie-fill', stops.length ? `conic-gradient(${stops.join(', ')})` : 'var(--bs-border-color)');
    pie.setAttribute('aria-label', 'Distribución del comparativo: ' + (shown.length
      ? shown.map(i => `${i.querySelector('span').textContent.trim()} $${money(Number(i.dataset.value))}`).join(', ')
      : 'sin series seleccionadas'));
    empty.hidden = total > 0;
  };
  toggles.forEach(t => t.addEventListener('change', render));
  render();
})();

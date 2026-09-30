/* Comparativo financiero. Dos filtros independientes:
   - chips de arriba ([data-series-toggle]): solo las barras (y su eje Y);
   - filas de la torta ([data-pie-toggle]): solo la torta.
   Además: eje Y abreviado, etiquetas del eje X en diagonal si no caben y
   tooltip por grupo (hover, foco de teclado y toque). */
(() => {
  const root = document.querySelector('[data-financial-chart]');
  if (!root) return;
  const toggles = [...root.querySelectorAll('[data-series-toggle]')];
  const chart = root.querySelector('[data-time-chart]');
  const bars = [...root.querySelectorAll('.gestor-time-bar[data-series]')];
  const buckets = [...root.querySelectorAll('[data-bucket]')];
  const axis = root.querySelector('[data-chart-axis]');
  const grid = root.querySelector('[data-chart-grid]');
  const labels = [...root.querySelectorAll('.gestor-time-label')];
  const tooltip = root.querySelector('[data-chart-tooltip]');
  const pie = root.querySelector('[data-financial-pie]');
  const pieToggles = [...root.querySelectorAll('[data-pie-toggle]')];
  const items = [...root.querySelectorAll('[data-pie-item]')];
  const empty = root.querySelector('[data-pie-empty]');
  const color = tone => getComputedStyle(document.documentElement).getPropertyValue('--bs-' + tone).trim() || '#888';
  // Formato COP con puntos como separador, igual que los campos monetarios.
  const money = n => '$ ' + String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');

  // ---- Eje Y: misma escala que financial_chart.axis_ticks (Python) ----
  const niceScale = maximum => {
    const max = maximum || 4000000;
    const raw = max / 4;
    const magnitude = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(f => f * magnitude).find(s => raw <= s) || 10 * magnitude;
    const count = Math.max(1, Math.ceil(max / step - 1e-9));
    const top = step * count;
    const [divisor, suffix] = top >= 1e6 ? [1e6, ' M'] : top >= 1e4 ? [1e3, ' K'] : [1, ''];
    const ticks = [];
    for (let i = 0; i <= count; i++) {
      const scaled = Math.round(step * i / divisor * 10) / 10;
      ticks.push({
        value: step * i,
        label: '$' + String(scaled).replace('.', ',') + suffix,
        position: i * 100 / count,
      });
    }
    return {top, ticks};
  };
  const drawAxis = ticks => {
    const make = (parent, tick, text) => {
      const span = document.createElement('span');
      span.style.setProperty('--pos', tick.position.toFixed(2) + '%');
      if (text) { span.textContent = tick.label; span.dataset.value = tick.value; }
      parent.appendChild(span);
    };
    axis.textContent = '';
    grid.textContent = '';
    ticks.forEach(tick => { make(axis, tick, true); make(grid, tick, false); });
  };

  // ---- Barras: filtro propio; la escala se recalcula con lo visible ----
  const active = () => new Set(toggles.filter(t => t.checked).map(t => t.dataset.seriesToggle));
  const renderBars = () => {
    const on = active();
    let max = 0;
    bars.forEach(bar => {
      const visible = on.has(bar.dataset.series);
      bar.hidden = !visible;
      if (visible) max = Math.max(max, Number(bar.dataset.value));
    });
    const {top, ticks} = niceScale(max);
    drawAxis(ticks);
    bars.forEach(bar => {
      const value = Number(bar.dataset.value);
      bar.style.setProperty('--bar-height', (value ? Math.round(value * 10000 / top) / 100 : 0) + '%');
      bar.classList.toggle('is-zero', !value);
    });
    hideTip();
  };

  // ---- Etiquetas del eje X: horizontales si caben, si no en diagonal ----
  const fitLabels = () => {
    chart.classList.remove('is-rotated');
    const overflow = labels.some(label => {
      const text = label.firstElementChild;
      return text.scrollWidth > label.clientWidth + 1;
    });
    chart.classList.toggle('is-rotated', overflow);
  };

  // ---- Tooltip ----
  function hideTip() {
    tooltip.hidden = true;
    buckets.forEach(b => b.classList.remove('is-hover'));
  }
  const showTip = (bucket, point) => {
    const rows = [...bucket.querySelectorAll('.gestor-time-bar[data-series]')].filter(b => !b.hidden);
    tooltip.textContent = '';
    const title = document.createElement('b');
    title.textContent = bucket.dataset.title;
    tooltip.appendChild(title);
    rows.forEach(bar => {
      const row = document.createElement('div');
      const swatch = document.createElement('i');
      swatch.className = 'bg-' + bar.dataset.tone;
      swatch.setAttribute('aria-hidden', 'true');
      row.appendChild(swatch);
      row.appendChild(document.createTextNode(bar.dataset.name + ': ' + money(Number(bar.dataset.value))));
      tooltip.appendChild(row);
    });
    buckets.forEach(b => b.classList.toggle('is-hover', b === bucket));
    tooltip.hidden = false;
    // Posición relativa al gráfico, sin salirse de sus bordes.
    const box = chart.getBoundingClientRect();
    const rect = bucket.getBoundingClientRect();
    const x = point ? point.x : rect.left + rect.width / 2;
    const y = point ? point.y : rect.top;
    const width = tooltip.offsetWidth || 0;
    const left = Math.min(Math.max(x - box.left + 12, 4), Math.max(4, box.width - width - 4));
    tooltip.style.left = left + 'px';
    tooltip.style.top = Math.max(4, y - box.top - tooltip.offsetHeight - 8) + 'px';
  };
  buckets.forEach(bucket => {
    bucket.addEventListener('mouseenter', e => showTip(bucket, {x: e.clientX, y: e.clientY}));
    bucket.addEventListener('mousemove', e => showTip(bucket, {x: e.clientX, y: e.clientY}));
    bucket.addEventListener('mouseleave', hideTip);
    bucket.addEventListener('focus', () => showTip(bucket));
    bucket.addEventListener('blur', hideTip);
    // Toque: el primer toque abre, otro sobre el mismo grupo lo cierra.
    bucket.addEventListener('click', e => {
      const wasTapped = bucket.dataset.tapped === '1';
      buckets.forEach(b => { b.dataset.tapped = ''; });
      if (wasTapped) { hideTip(); return; }
      bucket.dataset.tapped = '1';
      showTip(bucket, {x: e.clientX, y: e.clientY});
    });
  });
  document.addEventListener('click', e => { if (!chart.contains(e.target)) hideTip(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') hideTip(); });

  // ---- Torta: filtro propio, los porcentajes salen de lo visible ----
  const pieOn = () => new Set(pieToggles.filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.pieToggle));
  const renderPie = () => {
    const on = pieOn();
    const shown = items.filter(item => on.has(item.dataset.pieItem));
    const total = shown.reduce((sum, item) => sum + Number(item.dataset.value), 0);
    // Porcentajes enteros que suman 100 (mayores restos).
    const shares = new Map(shown.map(item => [item, total ? Number(item.dataset.value) * 100 / total : 0]));
    const whole = new Map([...shares].map(([item, share]) => [item, Math.floor(share)]));
    let left = total ? 100 - [...whole.values()].reduce((a, b) => a + b, 0) : 0;
    [...shares].sort((a, b) => (b[1] % 1) - (a[1] % 1)).forEach(([item]) => {
      if (left > 0 && shares.get(item) > 0) { whole.set(item, whole.get(item) + 1); left--; }
    });
    items.forEach(item => {
      item.classList.toggle('is-off', !on.has(item.dataset.pieItem));
      item.querySelector('[data-pie-share]').textContent = whole.get(item) || 0;
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
      ? shown.map(i => `${i.querySelector('span').textContent.trim()} ${money(Number(i.dataset.value))}`).join(', ')
      : 'sin series seleccionadas'));
    empty.hidden = total > 0;
  };

  toggles.forEach(t => t.addEventListener('change', renderBars));
  pieToggles.forEach(b => b.addEventListener('click', () => {
    b.setAttribute('aria-pressed', b.getAttribute('aria-pressed') === 'true' ? 'false' : 'true');
    renderPie();
  }));
  window.addEventListener('resize', fitLabels);
  if (window.ResizeObserver) new ResizeObserver(fitLabels).observe(chart);
  renderBars();
  renderPie();
  fitLabels();
})();

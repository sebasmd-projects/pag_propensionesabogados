(() => {
  const button = document.querySelector('.gestor-next-section');
  const TIP_DELAY = 1000;
  // Tooltip propio y accesible: aparece tras 1 s con el ratón encima o con el
  // foco, se enlaza con `aria-describedby` y se cierra con Escape, al salir,
  // al perder el foco o al pulsar. Sustituye al `title` nativo, que no se
  // ve con el teclado ni deja elegir el retraso.
  const attachTip = (target, lines, id) => {
    const tip = document.createElement('div');
    tip.id = id;
    tip.className = 'gestor-nav-tooltip';
    tip.setAttribute('role', 'tooltip');
    tip.hidden = true;
    lines.forEach(text => {
      const line = document.createElement('span');
      line.textContent = text;
      tip.appendChild(line);
    });
    document.body.appendChild(tip);
    target.removeAttribute('title');
    target.setAttribute('aria-describedby', id);
    let timer = null;
    const hide = () => { clearTimeout(timer); timer = null; tip.hidden = true; };
    const place = () => {
      const box = target.getBoundingClientRect();
      tip.style.right = Math.max(8, window.innerWidth - box.right) + 'px';
      tip.style.bottom = Math.max(8, window.innerHeight - box.top + 8) + 'px';
    };
    const schedule = () => {
      if (timer !== null || !tip.hidden) return;
      timer = setTimeout(() => { timer = null; place(); tip.hidden = false; }, TIP_DELAY);
    };
    target.addEventListener('mouseenter', schedule);
    target.addEventListener('focus', schedule);
    target.addEventListener('mouseleave', hide);
    target.addEventListener('blur', hide);
    target.addEventListener('click', hide);
    target.addEventListener('keydown', event => { if (event.key === 'Escape') hide(); });
    return tip;
  };
  let scrollTop = null;
  const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const sections = () => [...document.querySelectorAll('[data-gestor-section]')].filter(section => section.getClientRects().length);
  const next = () => sections().find(section => section.getBoundingClientRect().top > 130);
  const previous = () => {
    const visible = sections();
    const current = visible.reduce((found, section, index) => (
      section.getBoundingClientRect().top <= 130 ? index : found
    ), -1);
    return current > 0 ? visible[current - 1] : null;
  };
  const goTo = target => {
    if (!target) {
      window.scrollTo({top: 0, behavior: reducedMotion() ? 'instant' : 'smooth'});
      return;
    }
    target.tabIndex = -1;
    target.focus({preventScroll: true});
    target.scrollIntoView({behavior: reducedMotion() ? 'instant' : 'smooth', block: 'start'});
  };
  const update = () => {
    button.hidden = !next();
    if (scrollTop) {
      scrollTop.setAttribute('aria-label', 'Ir a la sección anterior; doble clic para volver al inicio');
    }
  };
  attachTip(button, ['Clic: sección siguiente'], 'gestor-next-section-tip');
  button.addEventListener('click', () => {
    goTo(next());
  });

  let singleClick;
  const previousClick = event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    clearTimeout(singleClick);
    if (event.detail === 0) {
      goTo(previous());
      return;
    }
    singleClick = setTimeout(() => goTo(previous()), 250);
  };
  const topDoubleClick = event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    clearTimeout(singleClick);
    goTo(null);
  };
  const bindScrollTop = () => {
    scrollTop = document.querySelector('.scroll-top');
    if (!scrollTop) return;
    scrollTop.dataset.sectionNavigation = 'true';
    attachTip(scrollTop, ['Clic: sección anterior', 'Doble clic: ir al inicio'], 'gestor-scroll-top-tip');
    scrollTop.addEventListener('click', previousClick);
    scrollTop.addEventListener('dblclick', topDoubleClick);
    update();
  };

  window.addEventListener('scroll', update, {passive: true});
  window.addEventListener('resize', update);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindScrollTop, {once: true});
  } else {
    bindScrollTop();
  }
  update();
})();

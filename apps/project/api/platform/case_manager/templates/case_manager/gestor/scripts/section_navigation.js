(() => {
  const button = document.querySelector('.gestor-next-section');
  const sections = () => [...document.querySelectorAll('[data-gestor-section]')].filter(section => section.getClientRects().length);
  const next = () => sections().find(section => section.getBoundingClientRect().top > 130);
  const update = () => { button.hidden = !next(); };
  button.addEventListener('click', () => {
    const target = next();
    if (!target) return;
    target.tabIndex = -1;
    target.focus({preventScroll: true});
    target.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start'});
  });
  window.addEventListener('scroll', update, {passive: true});
  window.addEventListener('resize', update);
  update();
})();

(() => {
  const button = document.querySelector('.gestor-next-section');
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
      scrollTop.title = 'Sección anterior · doble clic: volver al inicio';
    }
  };
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
    scrollTop.addEventListener('click', previousClick);
    scrollTop.addEventListener('dblclick', topDoubleClick);
    update();
  };

  const paymentFlow = document.querySelector('[data-payment-flow]');
  const configurePaymentFlow = () => {
    if (!paymentFlow) return;
    const payment = paymentFlow.querySelector('[data-payment-main]');
    const followups = paymentFlow.querySelector('[data-payment-followups]');
    paymentFlow.classList.remove('gestor-stage');
    paymentFlow.removeAttribute('data-gestor-section');
    payment.classList.remove('gestor-stage');
    payment.removeAttribute('data-gestor-section');
    followups.classList.remove('gestor-stage--compact');
    followups.removeAttribute('data-gestor-section');

    if (payment.getBoundingClientRect().height >= window.innerHeight * .85) {
      payment.classList.add('gestor-stage');
      payment.setAttribute('data-gestor-section', '');
      followups.classList.add('gestor-stage--compact');
      followups.setAttribute('data-gestor-section', '');
    } else {
      paymentFlow.classList.add('gestor-stage');
      paymentFlow.setAttribute('data-gestor-section', '');
    }
    update();
  };

  if (paymentFlow) {
    const body = paymentFlow.querySelector('[data-payment-main] .card-body');
    new MutationObserver(() => requestAnimationFrame(configurePaymentFlow)).observe(body, {
      subtree: true, childList: true, attributes: true,
      attributeFilter: ['class', 'hidden', 'style'],
    });
    configurePaymentFlow();
  }
  window.addEventListener('scroll', update, {passive: true});
  window.addEventListener('resize', () => {
    configurePaymentFlow();
    update();
  });
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindScrollTop, {once: true});
  } else {
    bindScrollTop();
  }
  update();
})();

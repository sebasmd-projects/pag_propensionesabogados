/* Formulario del cliente: el DV y el representante legal solo existen con NIT. */
(() => {
  const form = document.querySelector('form[data-client-form]');
  if (!form) return;
  const type = form.querySelector('[name="identification_type"]');
  if (!type) return;
  const number = form.querySelector('[data-client-id-number]');
  const name = form.querySelector('[name="full_name"]');
  const nitBoxes = [...form.querySelectorAll('[data-nit-only]')];

  const label = name && name.closest('[data-field-for]').querySelector('label');
  const setLabel = isNit => {
    if (!label || !name) return;
    const star = label.querySelector('span');
    label.textContent = (isNit ? name.dataset.labelCompany : name.dataset.labelPerson) + ' ';
    if (star) label.appendChild(star);
  };

  const apply = () => {
    const isNit = type.value === 'NIT';
    nitBoxes.forEach(box => {
      box.hidden = !isNit;
      box.classList.toggle('d-none', !isNit);
      // Un campo deshabilitado no se envia: pasar de NIT a CC no arrastra un
      // DV o un representante escritos antes, que el servidor rechazaria.
      box.querySelectorAll('input, select, textarea').forEach(el => { el.disabled = !isNit; });
    });
    if (number) number.setAttribute('inputmode', type.value === 'PA' ? 'text' : 'numeric');
    setLabel(isNit);
  };

  type.addEventListener('change', apply);
  apply();
})();

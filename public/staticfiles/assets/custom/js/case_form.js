/*
 * Los desplegables de clasificacion, encadenados.
 *
 * La cadena aprobada tiene tres eslabones y solo tres: servicio -> subtipo
 * (que en `Representación judicial` se lee como area) -> segundo subnivel
 * (el tipo concreto de proceso). Cada uno carga **unicamente** lo que cuelga
 * del anterior; el que no tiene nada que ofrecer se esconde en vez de
 * quedarse vacio delante de quien captura.
 *
 * Esconder no es validar: lo que se mande lo vuelve a comprobar
 * `CaseModel.clean()` en el servidor. Esto decide que se ve, no que vale.
 */
(() => {
  const source = document.getElementById('case-classification');
  if (!source) return;
  const catalog = JSON.parse(source.textContent);
  const field = name => document.getElementById(`id_${name}`);
  const service = field('service'), subtype = field('subtype');

  // El contenedor de la columna, para poder plegar el campo entero --etiqueta
  // incluida-- y no dejar un rotulo suelto sobre un hueco.
  const column = select => select.closest('[data-field-for]') || select.parentElement;

  const refill = (name, values) => {
    const select = field(name), previous = select.value;
    select.replaceChildren(
      new Option('---------', ''),
      ...values.map(value => new Option(value, value)),
    );
    select.value = values.includes(previous) ? previous : '';
    const box = column(select);
    const hide = values.length === 0;
    box.hidden = hide;
    box.classList.toggle('d-none', hide);
  };

  const updateOthers = () => {
    ['service', 'procedure', 'area', 'subtype', 'second_subtype'].forEach(name => {
      const input = field(`${name}_other`);
      const parent = field(name);
      const visible = !column(parent).hidden && /^(otro|otra)/i.test(parent.value);
      const container = input.closest('[data-other-for]');
      container.hidden = !visible;
      container.classList.toggle('d-none', !visible);
      input.required = visible;
    });
  };

  const updateSecond = () => {
    refill('second_subtype', catalog.seconds[service.value]?.[subtype.value] || []);
    updateOthers();
  };

  const updateClassification = () => {
    refill('subtype', catalog.subtypes[service.value] || []);
    refill('instance', catalog.instances[service.value] || []);
    updateSecond();
  };

  service.addEventListener('change', updateClassification);
  subtype.addEventListener('change', updateSecond);
  ['procedure', 'second_subtype'].forEach(
    name => field(name).addEventListener('change', updateOthers),
  );

  // No se reconstruye al abrir: las opciones que manda el servidor ya traen
  // el valor historico del expediente, y repintarlas aqui se lo comeria.
  // Lo que si se hace es plegar de entrada lo que no tiene nada dentro.
  [['second_subtype'], ['subtype'], ['instance']].forEach(([name]) => {
    const select = field(name);
    const vacio = select.options.length <= 1 && !select.value;
    column(select).hidden = vacio;
    column(select).classList.toggle('d-none', vacio);
  });
  updateOthers();

  // Abrir los bloques que ya traen datos o errores, aunque el exportado no
  // tenga tipo de tramite.
  ['bloqueJudicial', 'bloqueAdministrativo', 'bloquePolicivo'].forEach(id => {
    const block = document.getElementById(id);
    if (Array.from(block.querySelectorAll('input, select')).some(
      input => input.value || input.classList.contains('is-invalid'),
    )) {
      block.classList.add('show');
      const button = document.querySelector(`[data-bs-target="#${id}"]`);
      button.classList.remove('collapsed');
      button.setAttribute('aria-expanded', 'true');
    }
  });
})();

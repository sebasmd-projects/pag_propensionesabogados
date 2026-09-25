/*
 * Arranca DataTables en cada `<table data-datatable>` del gestor.
 *
 * Una sola inicializacion para todas las tablas y no una por pantalla: lo
 * que cambia de una a otra son las columnas, y eso se declara en el propio
 * `<th>` --`data-dt-no-sort`, `data-dt-order`-- en vez de en una lista de
 * indices que hay que renumerar cada vez que alguien mete una columna en
 * medio.
 *
 * Buscar, ordenar y paginar pasan a ocurrir en el navegador, con **todas**
 * las filas delante. Antes la busqueda y la paginacion eran del servidor, y
 * mezclar las dos cosas seria peor que cualquiera de las dos: DataTables
 * ordenaria los veinticinco de la pagina y diria que eso es el orden.
 *
 * Si el CDN no responde, esto no corre y la tabla se queda como esta: todas
 * las filas, sin ordenar. Se lee igual; solo se trabaja peor.
 */
(() => {
  if (typeof DataTable === 'undefined') return;

  // Los textos los pinta Django en un `<script type="application/json">`, no
  // el fichero de idioma de DataTables: asi la tabla habla el idioma de la
  // pagina y no el del navegador de quien mira.
  const fuente = document.getElementById('dt-i18n');
  const language = fuente ? JSON.parse(fuente.textContent) : {};

  // Con el tema de Bootstrap, DataTables pinta los botones de exportar como
  // `btn btn-secondary`: bloques grises macizos que pesan mas que el «Nuevo
  // cliente» de la esquina, que es la accion principal de la pantalla. Con
  // contorno se leen como lo que son: utilidades, no lo que hay que pulsar.
  if (DataTable.Buttons) {
    DataTable.Buttons.defaults.dom.button.className = 'btn btn-outline-secondary';
  }

  document.querySelectorAll('table[data-datatable]').forEach(tabla => {
    const cabeceras = [...tabla.querySelectorAll('thead th')];

    // Las columnas que no se ordenan lo dicen en su propio `<th>`: la de
    // acciones, que son botones, y la del paz y salvo, que es un formulario.
    // Ordenar por un `<form>` no significa nada.
    const columnDefs = [{
      targets: cabeceras
        .map((th, i) => (th.hasAttribute('data-dt-no-sort') ? i : -1))
        .filter(i => i >= 0),
      orderable: false,
      searchable: false,
    }];

    // El orden de entrada, si la tabla pide uno: `data-dt-order="3 desc"`.
    const pedido = (tabla.dataset.dtOrder || '').split(' ');
    const order = pedido[0] ? [[Number(pedido[0]), pedido[1] || 'asc']] : [];

    // Las tablas del panel van en media columna y no caben con los botones
    // de exportar ni con el menu de cuantas filas. Se quedan con lo que alli
    // hace falta --buscar, pasar de pagina y saber cuantas hay-- y con diez
    // filas, que es lo que ocupa la tarjeta sin crecer.
    const estrecha = tabla.hasAttribute('data-dt-compact');

    new DataTable(tabla, {
      language,
      order,
      columnDefs,
      pageLength: estrecha ? 10 : 25,
      lengthMenu: [10, 25, 50, 100],
      responsive: true,
      // El cuerpo se desplaza por dentro, asi que la cabecera de la tabla
      // --que dice que es cada columna-- y su pie --donde se pasa de pagina--
      // se quedan quietos. El alto de partida son cuatro quintos de la
      // pantalla; `encajar()`, mas abajo, lo baja si con eso el pie se saliera
      // por debajo, que es lo que hay que evitar.
      //
      // `scrollCollapse` evita lo contrario: una tabla de tres filas no deja
      // medio pantallazo de hueco blanco debajo.
      scrollY: estrecha ? '40vh' : '80vh',
      scrollCollapse: true,
      layout: estrecha ? {
        topStart: null,
        topEnd: 'search',
        bottomStart: 'info',
        bottomEnd: 'paging',
      } : {
        topStart: {
          buttons: {
            buttons: [
              'copy',
              'csv',
              { extend: 'pdf', orientation: 'landscape', pageSize: 'LETTER' },
              'print',
            ],
            className: 'btn-group-sm',
          },
        },
        topEnd: 'search',
        bottom2Start: 'pageLength',
        bottomStart: 'info',
        bottomEnd: 'paging',
      },
    });

    if (estrecha) return;

    // Cuatro quintos de pantalla es el techo, no la medida. Encima de la
    // tabla hay cabecera del sitio, titulo, pestanas y los botones de
    // exportar: con 80vh de cuerpo, el paginador quedaba **debajo** del
    // borde inferior y habia que bajar la pagina para pasar de pagina, que
    // es justo lo que se queria quitar.
    //
    // Asi que en vez de adivinar cuanto ocupa todo eso, se mide: el cuerpo se
    // queda con lo que va desde donde empieza hasta el borde de abajo, menos
    // lo que mide su pie. Se mide en coordenadas del documento para que
    // valga igual con la pagina desplazada.
    const contenedor = tabla.closest('.dt-container');
    const encajar = () => {
      const cuerpo = contenedor.querySelector('.dt-scroll-body');
      if (!cuerpo) return;
      cuerpo.style.maxHeight = '';
      const arriba = cuerpo.getBoundingClientRect().top + window.scrollY;
      // El pie no es un elemento: son las filas que DataTables pone **debajo**
      // de la de la tabla --contador, paginador, «Mostrar [25]»--, y son una
      // o dos segun la pantalla. Se suman las que haya, con su margen.
      const filas = [...contenedor.querySelectorAll(':scope > .row')];
      const tablaFila = filas.findIndex(f => f.classList.contains('dt-layout-table'));
      const altoPie = filas
        .slice(tablaFila + 1)
        .reduce((suma, fila) => suma + fila.getBoundingClientRect().height + 8, 0);
      const disponible = window.innerHeight - arriba - altoPie - 32;
      // El minimo evita que en una pantalla baja la tabla se quede en una
      // rendija de dos filas: alli es preferible que la pagina se desplace.
      const alto = Math.max(200, Math.min(window.innerHeight * 0.8, disponible));
      cuerpo.style.maxHeight = Math.round(alto) + 'px';
    };

    encajar();
    let pendiente;
    window.addEventListener('resize', () => {
      clearTimeout(pendiente);
      pendiente = setTimeout(encajar, 150);
    });
  });
})();

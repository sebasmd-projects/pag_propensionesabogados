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
  });
})();

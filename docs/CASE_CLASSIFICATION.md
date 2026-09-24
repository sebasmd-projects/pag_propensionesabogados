# Clasificación de los asuntos

El gestor utiliza los catálogos de `case_manager/choices.py` para los desplegables de subtipo, segundo subnivel e instancia. El servidor vuelve a validar las opciones enviadas. No se selecciona una especialidad automáticamente.

El flujo actual es Servicio → Área/Subnivel → Tipo concreto de proceso (cuando existe). Por ejemplo:

- Representación judicial → Laboral → Pensión de vejez.
- Representación judicial → Superintendencias → Protección al consumidor.

El trámite y el área del formato anterior se conservan como datos históricos ocultos. Los bloques administrativo y policivo con información previa quedan disponibles al editar. Los segundos subniveles históricos de texto libre fuera de la jerarquía actual pueden conservarse; los nuevos casos eligen sus opciones del catálogo.

Las opciones «Otro» / «Otra…» requieren una especificación separada. El modelo guarda esas descripciones en `service_other`, `procedure_other`, `area_other`, `subtype_other` y `second_subtype_other`. El portal, los listados y el paz y salvo muestran la descripción correspondiente.

La importación también interpreta `fi` con formato `YYYY-MM` como el primer día del mes y los abonos `pr` de cuota litis fija (0 %). Si `estadoPagoV29` es `PAGADO`, el importe pagado cubre al menos el valor fijo. Los saldos, deudores y totales descuentan esos abonos. Las cuotas litis porcentuales siguen siendo expectativas.

## Despliegue

Aplicar `python manage.py migrate` y ejecutar la recolección de estáticos del despliegue (`python manage.py collectstatic --noinput`). La migración 0005 añade los campos de especificación sin modificar la clasificación existente. La migración 0007 sincroniza las opciones de los catálogos que estaban pendientes en el repositorio; no reclasifica expedientes. El JavaScript del formulario se sirve desde su plantilla.

Para expedientes importados antes de este cambio, la información de pagos y fecha de inicio que el importador anterior omitió debe recuperarse del JSON original mediante `import_propdemo`. Revisar primero con `--dry-run`: una reimportación actualiza los datos incluidos en el archivo, por lo que debe utilizarse una exportación vigente.

## Flujo contrastado con el HTML y las notas de voz del 24/09/2026

La referencia es `ARBOL41`, con las etapas de `ETAPAS_V35` y los campos generales de `camposClaveV49` del archivo `MI_PROCESO_BASE_COMPLETA_WHATSAPP_2026-09-23.html`. El fixture `tests/fixtures/reference_flow.json` contiene únicamente esos catálogos, sin expedientes ni datos personales.

- Administrativo, conciliación, consultoría e investigación muestran su subnivel, sin un tercer selector vacío.
- Representación judicial muestra Área y, después de elegirla, Tipo concreto de proceso. Por ejemplo: Contencioso administrativo → Nulidad y restablecimiento del derecho.
- Otro conserva el campo de especificación solicitado; no muestra selectores hijos sin opciones.
- La instancia depende del servicio. Al cambiarlo se conserva solo si también existe en el nuevo servicio. Radicado y ciudad siguen disponibles; despacho solo corresponde a representación judicial.
- La respuesta HTML inicial ya oculta los campos que no aplican. La edición conserva los tres niveles y deja accesibles los detalles históricos existentes, aunque el antiguo tipo de trámite esté vacío.
- Al abrir un registro antiguo cuyo tipo concreto está en el catálogo pero carece de padres válidos, el formulario recupera la jerarquía únicamente si la coincidencia es única. No modifica la base al abrir: se guarda al confirmar el formulario. Los textos libres y las ramas válidas no se reclasifican.
- La distribución económica por área usa la rama judicial actual y conserva una alternativa para los registros anteriores.

### Verificación de la interacción DOM

Las pruebas Django recorren todas las ramas de la referencia. Para exportar páginas sintéticas de creación y edición, ejecutar `test_dynamic_flow` con `CASE_FLOW_HTML_DIR` apuntando a un directorio temporal, dentro del entorno de pruebas habitual. Después ejecutar `node apps/project/api/platform/case_manager/tests/dynamic_flow.cjs <directorio>` con `jsdom` disponible en `NODE_PATH`. La prueba ejecuta los scripts reales del formulario sobre esas páginas y comprueba carga inicial, cambios de rama, Otro, instancias y restauración de la edición. No requiere datos de producción.

# Clasificación de los asuntos

El gestor utiliza los catálogos de `case_manager/choices.py` para los desplegables de subtipo, segundo subnivel e instancia. El servidor vuelve a validar las opciones enviadas. No se selecciona una especialidad automáticamente.

Representación judicial admite tanto la clasificación por área anterior como la jerarquía judicial exportada en `st` / `st2`. Por ejemplo:

- Pensional / Seguridad Social → Laboral → Pensión de vejez.
- Sin área registrada → Superintendencias → Protección al consumidor.

El trámite y el área siguen siendo opcionales. Al editar se conservan los valores del expediente; los bloques judicial, administrativo y policivo que contienen datos o errores se abren al cargar el formulario. Los segundos subniveles históricos de texto libre fuera de la jerarquía judicial pueden conservarse, pero no se admiten nuevos textos arbitrarios desde el formulario.

Las opciones «Otro» / «Otra…» requieren una especificación separada. El modelo guarda esas descripciones en `service_other`, `procedure_other`, `area_other`, `subtype_other` y `second_subtype_other`. El portal, los listados y el paz y salvo muestran la descripción correspondiente.

La importación también interpreta `fi` con formato `YYYY-MM` como el primer día del mes y los abonos `pr` de cuota litis fija (0 %). Si `estadoPagoV29` es `PAGADO`, el importe pagado cubre al menos el valor fijo. Los saldos, deudores y totales descuentan esos abonos. Las cuotas litis porcentuales siguen siendo expectativas.

## Despliegue

Aplicar `python manage.py migrate` y ejecutar la recolección de estáticos del despliegue (`python manage.py collectstatic --noinput`). La migración 0005 añade los campos de especificación sin modificar la clasificación existente.

Para expedientes importados antes de este cambio, la información de pagos y fecha de inicio que el importador anterior omitió debe recuperarse del JSON original mediante `import_propdemo`. Revisar primero con `--dry-run`: una reimportación actualiza los datos incluidos en el archivo, por lo que debe utilizarse una exportación vigente.

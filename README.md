# PROPENSIONES

1. Estructura de Ramas
    master: La rama de producción, solo debe contener código aprobado y probado.
    develop: La rama de desarrollo principal. Aquí se integran nuevas funcionalidades antes de enviarlas a producción.
        feature/: Ramas para cada nueva funcionalidad, nombradas según el objetivo, por ejemplo, feature/authentication o feature/customer-crud.
        bugfix/: Ramas específicas para solucionar bugs detectados en producción o desarrollo, por ejemplo, bugfix/form-validation.
        hotfix/: Para corregir problemas críticos en producción, por ejemplo, hotfix/security-fix.
    release/: Ramas dedicadas para preparar una nueva versión antes de ser liberada en producción, por ejemplo, release/v1.0.

2. Convenciones para Commits
    version: para definir un release.
    feat: para nuevas funcionalidades.
    fix: para arreglos de bugs.
    refactor: para refactorización de código sin cambios funcionales.
    docs: para cambios en documentación.
    test: para cambios en pruebas o nuevas pruebas.
    config: para cambios en configuraciones.
    chore: para tareas de mantenimiento (actualización de dependencias, etc.).
        Ejemplo: feat: agregar endpoint de registro en CRM.

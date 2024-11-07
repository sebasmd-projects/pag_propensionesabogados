# Atlas

1. Estructura de Ramas
    main: La rama de producción, solo debe contener código aprobado y probado.
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

3. Workflow de Git
    Creación de rama:
        Crea una rama a partir de develop para cada nueva funcionalidad o corrección.
    Commits y Push:
        Realiza commits con frecuencia siguiendo las convenciones establecidas.
        Haz push de la rama cuando los cambios estén listos para revisión.
    Pull Requests (PR):
        Cuando termines una funcionalidad, abre un Pull Request (PR) hacia la rama develop o hacia la rama correspondiente (release o main en caso de hotfix).
        Revisa los PR de tus compañeros para asegurar un flujo de revisión y control de calidad.
    Merge:
        Después de que un PR sea aprobado, haz merge a develop.
        Para releases, usa la rama release/x.x, y haz merge a main solo después de pruebas exhaustivas.

4. Pipeline de CI/CD (Integración y Despliegue Continuo)
    Ramas de feature/* y bugfix/*: Ejecuta pruebas unitarias y de integración.
    Rama develop: Despliega automáticamente a un entorno de desarrollo y ejecuta pruebas de integración adicionales.
    Rama release/*: Despliega a un entorno de preproducción para realizar pruebas de aceptación.
    Rama main: Despliega automáticamente a producción solo después de que todos los tests hayan pasado.

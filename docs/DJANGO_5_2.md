# Subida a Django 5.2

De **4.2.21** a **5.2.17**. Este documento dice qué se comprobó, qué hubo que
cambiar y qué hay que vigilar la próxima vez.

> ⚠️ **Si el motor es MariaDB 10.7 o superior, lee la §3 antes de desplegar.**
> Django 5.0 cambió cómo se escriben los UUID en las consultas, y con una base
> creada por Django 4.2 eso rompe el acceso **sin dar ningún error**. Ya está
> resuelto en el código; lo que hay que saber es que no se puede quitar.

---

## 1. Checklist de cambios rompedores

Cada línea se comprobó **contra este código**, no contra las notas de versión.
«No aplica» quiere decir que se buscó y no hay ni un uso.

### Django 5.0

| Cambio | ¿Afecta? | Comprobado |
|---|---|---|
| **`UUIDField` pasa al tipo nativo `uuid` en MariaDB 10.7+** | **Sí, y rompe el acceso** | Ver §3 |
| Se quita `django.utils.timezone.utc` | No | Sin usos |
| Se quita el soporte de `pytz` y `USE_DEPRECATED_PYTZ` | No | Sin usos |
| Se quita `USE_L10N` | No | No está en `settings.py` |
| Se quitan `CryptPasswordHasher`, `UnsaltedMD5`, `UnsaltedSHA1` | No | `PASSWORD_HASHERS` empieza por Argon2 |
| Python mínimo 3.10 | No | El proyecto pide 3.11 |
| `forms.URLField` pasará a asumir `https` (transición a 6.0) | No | Los 9 `URLField` son de modelo, no de formulario |

### Django 5.1

| Cambio | ¿Afecta? | Comprobado |
|---|---|---|
| Se quitan `DEFAULT_FILE_STORAGE` y `STATICFILES_STORAGE` | No | No estaban en `settings.py` |
| Se quita `Meta.index_together` | No | Sin usos |
| Se quita el filtro de plantilla `length_is` | No | Sin usos en las plantillas |
| Se quita `BaseUserManager.make_random_password()` | No | Sin usos |
| Se quita `django.core.files.storage.get_storage_class()` | No | Sin usos |
| `ModelAdmin.log_deletion()` → `log_deletions()` | No | El admin no los sobrescribe |
| `CheckConstraint.check` → `.condition` | No | No hay ni una `CheckConstraint` |
| `LoginRequiredMiddleware` (nuevo, opcional) | No se adopta | El sitio es mayoritariamente público |

### Django 5.2

| Cambio | ¿Afecta? | Comprobado |
|---|---|---|
| **Mínimos de base de datos** (MySQL 8.0.11, MariaDB 10.5, PostgreSQL 14) | **Sí, en el servidor** | Hay que confirmarlo contra la base de producción antes de desplegar |
| `Model.save()` con argumentos posicionales queda obsoleto | No | Ningún `save(True)`; los `save()` propios usan `*args, **kwargs` |
| Se quita `DjangoDivFormRenderer` | No | No se toca `FORM_RENDERER` |
| Claves primarias compuestas (nuevo) | No se usa | — |

---

## 2. Cómo se comprobó

La suite del proyecto estaba **vacía** antes de esta subida (todos los
`tests.py` eran el stub de `startapp`), así que el checklist de arriba se
apoya en tres cosas distintas, ninguna de ellas «lo dicen las notas»:

1. `manage.py check` — 0 issues.
2. `manage.py makemigrations --check --dry-run` — sin cambios pendientes.
3. **Prueba de humo contra el sitio levantado**: `/` 200, `/admin/` 200,
   `/consultar/proceso/` 200, `/api/swagger/` 403 (el esperado: pide
   `IsAdminUser`). `collectstatic` reprocesa 434 ficheros sin error.

Más las pruebas nuevas de `app_core/tests/`, que son las primeras del
repositorio.

---

## 3. Los UUID se siguen guardando como estaban (MariaDB 10.7+)

**Es el cambio que más daño hace y el que no aparece como cambio de datos.**

Django 5.0 empezó a usar el tipo nativo `uuid` de MariaDB 10.7 o superior:

```python
# django/db/backends/mysql/features.py
@cached_property
def has_native_uuid_field(self):
    is_mariadb = self.connection.mysql_is_mariadb
    return is_mariadb and self.connection.mysql_version >= (10, 7)

# django/db/models/fields/__init__.py, UUIDField.get_db_prep_value
if connection.features.has_native_uuid_field:
    return value          # con guiones: 'd717d90c-5e8c-45a7-...'
return value.hex          # sin guiones: 'd717d90c5e8c45a7...'
```

Una base creada con Django 4.2 tiene la columna como `char(32)` y los valores
en hex **sin guiones**. Al subir, las consultas pasan a mandar el UUID **con
guiones** contra esa misma columna.

Aquí eso alcanza a cuatro módulos con clave primaria `UUIDField` —`users`,
`core`, `auth_platform` e `insolvency_form`— y a las siete migraciones que las
crearon, todas escritas bajo Django 4.2.

**No falla: se queda en silencio.** La fila existe, se lee, y
`filter(username=...)` la encuentra; sólo deja de funcionar lo que busca **por
clave primaria**. En el acceso eso significa que la contraseña se acepta —el
backend de `apps/common/utils/backend` busca por `username` o por `email`— y
acto seguido la sesión no puede recargar al usuario por su pk.

**Se apaga en vez de migrar la base.** `app_core/db/mysql` es el backend de
Django con `has_native_uuid_field = False`, y `settings.py` lo instala cuando
el `.env` declara MySQL (`app_core/db/engine_for()`). Migrar sería convertir
esas columnas **y todas las claves ajenas que apuntan a ellas** en una base en
producción, de una vez y sin poder volver atrás a mitad. El tipo nativo no
aporta nada que este proyecto use: lo que aporta es que MariaDB muestre el
UUID formateado.

Apagarlo devuelve exactamente el comportamiento con el que se escribieron esos
datos, y es reversible: migrar sigue siendo posible el día que compense.

En MySQL (el de Oracle, no MariaDB) y en PostgreSQL esto no cambia nada.

La decisión vive en `app_core/db/engine_for()` para poder probarla, y la fija
`app_core/tests/test_db_backend.py`.

---

## 4. Lo demás que hubo que cambiar

### 4.1 `django-honeypot` se queda en 1.2.1, con un override

La 1.2.1 declara `django<5.2`. La 1.3.0 sí soporta 5.2 **pero exige Python
3.12**, y subir el intérprete del servidor es otra decisión, no un efecto
colateral de esta.

El techo de la 1.2.1 es de metadatos, no una incompatibilidad conocida: el
paquete es un decorador, un middleware y una etiqueta de plantilla. El
proyecto lo salta con el mecanismo de uv (`pyproject.toml`, `[tool.uv]
override-dependencies`), que es de primera clase porque el repositorio ya se
gestiona con uv (`uv.lock`).

**Un override que nadie comprueba es una suposición.** Por eso está
`app_core/tests/test_honeypot.py`, que ejercita las tres cosas que el proyecto
usa de verdad: la etiqueta que pinta el campo, un envío legítimo que pasa y
uno con el campo relleno que se rechaza.

El día que se suba a Python 3.12, esto se cae solo: `django-honeypot==1.3.0` y
fuera el override.

### 4.2 Paquetes que hubo que subir con Django

| Paquete | De | A | Por qué |
|---|---|---|---|
| `django-parler` | 2.3 | 2.4 | La 2.3 no declara 5.2 |
| `django-auditlog` | 3.0.0 | 3.4.1 | Registra todos los modelos del proyecto |
| `django-import-export` | 4.0.8 | 4.4.1 | Arrastra `tablib` y `diff-match-patch` |
| `django-debug-toolbar` | 4.4.2 | 8.0.0 | La 8.0 pide `django>=5.2` |
| `django-nested-admin` | 4.0.2 | 4.1.6 | — |
| `django-admin-sortable2` | 2.2.1 | 2.3.1 | — |
| `django-cors-headers` | 4.3.1 | 4.9.0 | — |
| `django-ckeditor-5` | 0.2.13 | 0.2.20 | — |
| `django-rosetta` | 0.10.0 | 0.10.3 | — |
| `djangorestframework` | 3.15.2 | 3.16.1 | La 3.15 no declara 5.2 |
| `djangorestframework-simplejwt` | 5.3.1 | 5.5.1 | — |
| `django-filter` | 24.2 | 25.2 | — |
| `django-cleanup` | 8.1.0 | 9.0.0 | — |
| `tablib` | 3.5.0 | 3.8.0 | Lo exige `django-import-export` |
| `diff-match-patch` | 20230430 | 20241021 | Lo fija `django-import-export` |

### 4.3 Una migración que faltaba

`makemigrations --check` destapó una deriva **anterior** a esta subida:
`PqrsModel.address` tiene `default=''` en el modelo desde que se renombró
`addres` → `address` (migración `0003`), pero nadie generó la migración. Se
generó como `0004_alter_pqrsmodel_address`. Es un atributo de Django, no
toca datos.

---

## 5. Antes de desplegar

1. **Confirmar la versión del motor** contra el mínimo de Django 5.2
   (MySQL 8.0.11 / MariaDB 10.5).
2. **Entrar una vez al admin contra la base de verdad.** Es lo único que
   demuestra que el §3 está bien resuelto: la suite corre sobre SQLite y ahí
   este fallo no existe. Ésta fue la lección que se pagó en GEA.
3. `pip install -r requirements.txt` **no vale** mientras esté el override de
   honeypot: el despliegue tiene que usar `uv sync` (o `uv pip install`), que
   es lo que lee `[tool.uv]`.

---

## 6. Trampa que queda abierta

`apps/common/utils/migrations/__init__.py` **no está vacío**: declara una clase
`Migration` con `UnaccentExtension()` y `TrigramExtension()`, que son de
PostgreSQL. Django no ejecuta nunca el `__init__.py` de un paquete de
migraciones, así que esas extensiones **no se aplican**; lo único que consigue
el fichero es obligar a que `psycopg2` esté instalado para poder correr
`migrate` en un proyecto que va sobre MySQL.

No se tocó en esta subida porque no es suyo, pero conviene vaciarlo: hoy
funciona por accidente.

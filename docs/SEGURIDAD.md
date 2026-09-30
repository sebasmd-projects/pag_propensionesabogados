# Plan de seguridad — seguimiento

Hallazgos de la revisión del **25 de septiembre de 2026**. La Fase 1 queda
cerrada el **29 de septiembre de 2026**: los puntos 1, 2 y 3 están corregidos.
El **30 de septiembre de 2026** se corrige el 4 (CORS) y el 5 queda en su
primera etapa (CSP en modo solo informe). Ese mismo día se trae de gea el
conjunto de comprobaciones y respaldos (`check_security`, `db_backup`…): ver el
«Checklist antes de desplegar» y «Cerrado en la T3.7». Se conserva el
diagnóstico original como referencia; los hallazgos 6 a 8 siguen pendientes.

## Checklist antes de desplegar

Cuatro comandos antes, uno después. Si salen limpios, adelante.

```bash
python manage.py check --deploy       # ajustes de Django: cero ERRORS
python manage.py check_security       # la superficie propia de este proyecto
python manage.py check_requirements   # que lo instalado sea lo de requirements.txt
python manage.py check_attack_terms   # que la trampa anti-escaneo no se coma una ruta propia
```

Y **una vez desplegado**, para comprobar que responde de verdad y no solo por dentro:

```bash
python manage.py check_health --http  # pide PUBLIC_BASE_URL/health/
python manage.py check_media --http   # un PDF privado, pedido por MEDIA_URL, no se entrega
```

Lanzarlos **donde corre la aplicación**, con el `.env` de producción
(`DJANGO_DEBUG` distinto de `True`): con el de desarrollo salen avisos que no
son de producción (`DEBUG`, cookies sin `Secure`) y se les acostumbra uno.
`check_security` también está pensado para CI con `--strict` (sale con código
distinto de cero si hay algún hallazgo). Otros comandos de apoyo:
`check_cache` (¿la caché se comparte entre procesos?), `check_health` (dentro
del proceso: base de datos, caché, correo y sesiones), `check_media` (¿están los
ficheros donde dice `MEDIA_ROOT`?), `rotate_logs` / `show_log` (el log),
`db_backup` / `db_restore_open` (respaldos, más abajo) y `test_report`.

`check_security` incluye además tres escáneres de fuera:

| | Qué mira | Dónde corre | Credencial |
|---|---|---|---|
| **bandit** | el código | servidor y local | ninguna |
| **pip-audit** | las dependencias instaladas | servidor y local | **ninguna** |
| **safety** | lo mismo, con una base más rica | **sólo local** | `SAFETY_API_KEY` |

```bash
pip install bandit pip-audit        # servidor o local
uv add --dev bandit pip-audit safety  # local, con uv
```

**`pip-audit` es la de producción, y lo es precisamente porque no lleva
credencial**: no hay clave que rotar ni que se pueda filtrar, y mira el
**entorno instalado**, no `requirements.txt`. **`safety` se queda en local**:
Safety CLI 3 siempre se autentica y en un servidor eso es un cuelgue; saltársela
allí no cuenta como hueco. Los tres son opcionales y no están en
`requirements.txt`: lo que falte **sin estar previsto** sale aparte, al final
del informe (`SIN MIRAR`), porque un «sin hallazgos» que se ha saltado una
sección entera es una media verdad. Los avisos de bandit que se dan por buenos
están razonados uno a uno en `apps/common/utils/scanners.py` (`BANDIT_ACCEPTED`).

### Y esto a ojo

| | Qué mirar | Por qué |
|---|---|---|
| ☐ | `DJANGO_DEBUG` **no** es `True` | Con `DEBUG` cada error muestra la traza entera, con ajustes y consultas dentro; además apaga HSTS, `Secure` de las cookies y la redirección a HTTPS |
| ☐ | `SERVER_KEY` de 32+ caracteres y **la misma** en pag, gea y Vercel | Protege la API de Attlas, decide si se cree `X-Client-IP` y es la clave del emisor ante gea. Cambiarla en un solo sitio corta el paz y salvo certificado (sección «Clave servidor a servidor») |
| ☐ | `FIELD_ENCRYPTION_KEY` es la misma de siempre | Cambiarla **inutiliza la cédula y la fecha de nacimiento ya cifradas**. No se rota sin migrar los datos |
| ☐ | `PRIVATE_MEDIA_ROOT` puesta y **fuera de `public_html`** | Ahí viven los PDF del paz y salvo. Si cae bajo el árbol que publica el servidor web, se reparten sin pasar por Django. Sin la variable, cae en `BASE_DIR/private_media`: en cPanel, comprueba que ese directorio no cuelga de `public_html` (`check_security` y `check_media` lo avisan) |
| ☐ | `BACKUP_PASSPHRASE` puesta **antes** de respaldar, y guardada aparte | `dumpdata` serializa el valor **descifrado**: sin frase, `db_backup` no escribe el volcado con datos personales. Quien pierda la frase pierde los respaldos |
| ☐ | `CORS_ALLOWED_ORIGINS` con los orígenes de verdad, sin comodines | Enumerados, con esquema y sin barra final. Un origen legítimo que falte se **añade** a la variable; no se vuelve al comodín |
| ☐ | `COMMON_ATTACK_TERMS` pasa `check_attack_terms` | Un término que sea un segmento de una ruta propia (`setup` lo es de `accounts/two_factor/setup/`) bloquea a quien la visita |
| ☐ | `DJANGO_ADMIN_URL` no es `admin/` | Es la primera ruta que prueba cualquier escáner |
| ☐ | `pip install -r requirements.txt` ejecutado | `check_requirements` compara lo instalado con lo fijado; producción instala con `pip`, no con `uv` |
| ☐ | `migrate` y `collectstatic` ejecutados | Una restricción sin migrar no existe; un JS sin recoger no llega |
| ☐ | `.htaccess` en `DJANGO_MEDIA_ROOT` (ver «Media» más abajo) | No hay carpetas sensibles bajo `MEDIA_ROOT`, pero conviene apagar la ejecución de scripts y los listados |
| ☐ | El correo sale de verdad | El acceso con código al buzón y la recuperación de clave dependen de él: `DJANGO_EMAIL_*` completas y una prueba de envío |
| ☐ | Caché compartida (o asumir el límite por worker) | Sin `CACHES`, Django usa `LocMemCache`, que es por proceso: los cupos de intentos se multiplican por el número de workers. `check_cache` y `check_security` lo señalan |

---

## Cerrado en la T3.7 (integración de lo compartido con gea)

### Recursos de terceros: versión fija e `integrity`

Se recorrieron **todas las plantillas** (las de las apps y `templates/`) y los
CSS propios buscando `<script src>`, `<link href>` y `@import` de terceros.
Con `integrity="sha384-…"` + `crossorigin="anonymous"`, hash calculado sobre el
fichero **exacto** descargado (y luego borrado):

| Recurso | Dónde | Versión fijada |
|---|---|---|
| DataTables (CSS y JS, paquete a medida) | gestor, `case_manager/gestor/partials/datatables*.html` | `dt-3.1.1` … `sl-4.1.0` |
| pdfmake + `vfs_fonts.js` | gestor, `datatables_js.html` | `pdfmake@0.3.11` |
| Swagger UI (CSS, bundle, standalone) | `/api/swagger/` (solo personal) | `swagger-ui-dist@5.33.0` |
| ReDoc | `/api/redoc/` (solo personal) | `redoc@2.5.4` |

Las cuatro primeras ya venían firmadas y se **verificaron** contra el fichero
del CDN (coinciden). Swagger UI y ReDoc **no**: `drf-spectacular` los carga de
jsDelivr `@latest` y sin `integrity`. Se fijó la versión en
`SPECTACULAR_SETTINGS` y se sustituyeron sus dos plantillas por las de
`templates/drf_spectacular/`, que llevan los hashes. **Al subir de versión hay
que volver a sacarlos**: si no, el navegador se niega a ejecutar el recurso
(fallo visible, que es lo que se busca).

**Excepciones**, todas mutables por diseño y declaradas con su motivo en
`apps/common/utils/tests/test_sri.py`:

| | Por qué no admite hash | Qué haría falta |
|---|---|---|
| `fonts.googleapis.com` (Google Fonts CSS, `base.html` y ReDoc) | Su contenido cambia según el navegador que lo pide y Google lo actualiza sin avisar | Alojar las fuentes en el propio sitio |
| reCAPTCHA (`www.google.com`, `www.gstatic.com`, `www.recaptcha.net`) | `api.js` es un cargador sin versión que Google exige cargar de su URL; lo inserta el widget de `django-recaptcha`, no una plantilla nuestra | Nada: es la contrapartida de usar reCAPTCHA. Está acotado por la CSP |

No son recursos ejecutables y no admiten `integrity`: el icono de Trace
(`tracecertificates.com`, una imagen en la cabecera) y las etiquetas `<link>`
que no cargan código (`preconnect`, `canonical`, `alternate`, iconos).

`test_sri.py` **falla si aparece un tercero nuevo sin firmar** o sin estar en las
excepciones, si una URL de jsDelivr no lleva versión, si un `integrity` no lleva
`crossorigin`, o si Swagger/ReDoc pierden su hash.

### `drf_spectacular.E001` en `check --deploy`

**Causa:** `ClientViewSet.get_authenticators()`
(`apps/project/api/platform/calculator/api/views.py`) leía
`self.request.method` para elegir el autenticador. `drf-spectacular` construye
la vista con `request = None` y llama a `initialize_request()` **antes** de
asignarle la petición simulada, así que `self.request` era `None` y saltaba un
`AttributeError`. En una petición real no pasa (Django deja `self.request`
puesto antes de despachar), por eso nadie lo vio navegando: solo fallaba al
generar el esquema, o sea en `check --deploy`, en `manage.py spectacular` y en
`/api/schema/`, que daba 500 (comprobado con el código anterior): las páginas de
Swagger y ReDoc cargaban, pero sin esquema que pintar.

**Arreglo:** el método se toma de la petición que recibe `initialize_request()`
(la misma que usa DRF). Ninguna ruta cambia de autenticador, y
`app_core/tests/test_openapi_schema.py` lo comprueba para las cuatro acciones.
El esquema **público** (rutas, métodos, permisos) no se toca: antes no se podía
generar, ahora sí.

**Avisos que quedan** en `check --deploy` con el `.env` de producción (0 errores),
todos de calidad de la documentación generada y ninguno de seguridad:

- `drf_spectacular.W001/W002` (16): serializadores sin adivinar en cinco vistas
  `APIView` de `auth_platform` (falta `serializer_class` o `@extend_schema`),
  tres `get_*` de serializador sin tipo (`get_category`, `get_category_en`,
  `get_signed`), tres autenticadores propios sin `OpenApiAuthenticationExtension`
  (`LookupOrPlatformTokenAuthentication`, `BearerTokenAuthentication`), un
  choque de nombres de enumeración (`RequestTypeEnEnum`) y tres `operationId`
  repetidos en `insolvency-form/`. Arreglarlos cambia el **esquema público**
  (nombres de operaciones y componentes), que era lo que había que evitar en
  esta tarea; quedan para una limpieza aparte.
- `security.W019`: `X_FRAME_OPTIONS = 'SAMEORIGIN'` a propósito; la página de
  documentos incrusta sus PDF (`<embed>`) desde el propio sitio.

### Respaldos: que no deshagan el cifrado de campo

`dumpdata` serializa el **valor de Python** de cada campo, y en los de
`django-encrypted-model-fields` ese valor es el ya descifrado: la cédula y la
fecha de nacimiento de los clientes de la plataforma salían **en claro** en el
respaldo. `FIELD_ENCRYPTION_KEY` protege la base de datos contra un volcado
robado, y el volcado de al lado era ese volcado robado ya servido.

Ahora `manage.py db_backup` cifra con Fernet y una clave derivada por scrypt de
`BACKUP_PASSPHRASE` (o, si falta, `GEA_BACKUP_PASSPHRASE`; el formato es el mismo
que el de gea), escribe todo con permisos 600 —abriendo el fichero ya con
ellos— y **sin frase no escribe la PII** (`--allow-plaintext` la pide a mano).
Se abre con `manage.py db_restore_open`, que **no carga nada**: deja el JSON
para `loaddata`, y ese JSON lleva datos personales en claro (bórralo al acabar).

**Qué cubre.** Dos volcados, cada uno en versión legible (`h_*`) y compacta:

- `backup.json`, **sin PII**: `core` (equipo, avisos modales; sin
  `core.ContactModel`), `faq`, `financial_education`, `calculator`.
- `pii_backup.json.enc`, **cifrado**: `users`, `account`, `auth_platform`
  (clientes de la plataforma y asesores), `case_manager` (clientes, asuntos,
  finanzas, notas y paz y salvo del gestor), `insolvency_form` (formulario de
  insolvencia, con la firma en base64), `pqrs`, `core.ContactModel` y `utils`
  (IP bloqueadas y de la lista blanca).

**Qué no cubre**, y conviene saberlo: no es un respaldo completo de la
plataforma.

- Los **ficheros**: `MEDIA_ROOT` y sobre todo `PRIVATE_MEDIA_ROOT` (los PDF del
  paz y salvo, original y copia) son disco, no filas. Hay que copiarlos aparte,
  y los PDF llevan datos personales: cifrados también.
- `auditlog.LogEntry` (lleva instantáneas de los registros con su PII),
  `axes`, `sessions` y `admin.LogEntry`.
- El **segundo factor** (`django_otp`, `two_factor`): tras restaurar, cada
  usuario tiene que volver a enrolar el suyo.
- `auth.Group` y `auth.Permission`: el grupo del gestor se recrea con
  `manage.py setup_case_manager_group` **antes** de `loaddata`, y hay que
  comprobar después la pertenencia de cada usuario.
- El esquema: `dumpdata` guarda datos; el esquema lo crea `migrate`.

El volcado general **se niega a escribirse** si una app con PII entra en su
lista, o si algún modelo suyo tiene un campo cifrado
(`utils/tests/test_backup.py`).

### Log rotable

`settings.LOGGING` usa `WatchedFileHandler` sobre `LOG_FILE`
(`DJANGO_LOG_FILE` o `BASE_DIR/stderr.log`). Con el `FileHandler` de antes,
rotar el fichero (`rotate_logs`) dejaba a todos los workers escribiendo en el
renombrado y el nuevo se quedaba vacío. Formato y nivel son los mismos del
`basicConfig` que sustituye (WARNING en la raíz); la ruta es ahora absoluta, no
relativa al directorio de trabajo. En Windows rotar no funciona con la
aplicación levantada (no se puede renombrar un fichero abierto): es cosa del
servidor.

### Media

Bajo `MEDIA_ROOT` solo hay contenido del sitio (`team/`, `modal_banners/` y lo
que sube CKEditor 5 a la raíz, solo imágenes y solo `is_staff`). Lo sensible
—los PDF del paz y salvo— vive en `PRIVATE_MEDIA_ROOT`, sin URL. La firma y el
DOCX de `insolvency_form` no tocan disco (base64 en la base de datos y
`BytesIO`). `check_security` y `check_media` (`utils/media_audit.py`) exigen que
cada carpeta bajo `MEDIA_ROOT` esté declarada servible con su razón, y que
`PRIVATE_MEDIA_ROOT` quede fuera de `MEDIA_ROOT`, de `STATIC_ROOT` y de
`public_html`.

Pag **no tiene** `deploy/media.htaccess`, y hoy no hace falta para ocultar nada.
Conviene uno de defensa en profundidad para `DJANGO_MEDIA_ROOT`
(copiar a `MEDIA_ROOT/.htaccess`): que nada de lo subido se ejecute ni se liste,
y que un directorio sensible que alguien cree mañana nazca cerrado.

```apache
# MEDIA_ROOT/.htaccess
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule ^(paz_y_salvo|private_media|test_reports)(/|$) - [R=404,L]
</IfModule>
<IfModule mod_php.c>
    php_flag engine off
</IfModule>
Options -ExecCGI -Indexes
AddType text/plain .php .phtml .php3 .php4 .php5 .php7 .php8 .pl .py .cgi .sh
```

### Trampa anti-escaneo

`check_attack_terms` necesitaba el patrón de gea (el término tiene que ser un
**segmento completo** de la ruta), así que se trajo `attack_patterns.py`: pag
tenía todavía el original, que buscaba el término como **subcadena** suelta.
Con los términos del `.env` de desarrollo (`old`, `env`, `wp`, `html`,
`setup`…) cualquier ruta que los llevara dentro —un miembro del equipo cuyo
enlace fuera `golden-team`— caía en la trampa y bloqueaba la IP del usuario.

### Hallazgos abiertos de `check_security`

Reales de pag, **sin arreglar** (no son triviales: hay que decidir el cupo):

1. **Sin límite de intentos** en cuatro formularios públicos:
   `POST /accounts/register/` (crea cuentas sin freno, aunque nacen sin
   permisos), `POST /api/v1/contact/` y `POST /api/v1/pqrs/` (públicos, sin
   captcha) y el formulario de contacto de la portada (`core:index`; este sí
   lleva honeypot y reCAPTCHA, que lo mitigan, pero no hay cupo). Usar
   `RateLimit` (`utils/throttling.py`), como el resto de puntos de entrada.
2. **Caché no compartida** (`LocMemCache`): los cupos son por worker.
3. Con el `.env` de **desarrollo**: `COMMON_ATTACK_TERMS` incluye `setup`, que
   secuestra `accounts/two_factor/setup/` (`check_attack_terms`). El de
   `docs/env.example` no lo tiene; revisar el de producción.

---

## Auditoría — lo que se encontró

Cada punto trae el fichero y la línea, por qué importa y cómo comprobar que
quedó bien. Las líneas son de `7c35a5c`; si el fichero cambió, busca por el
nombre de la clase.

Lo que sí está hecho y no se repite aquí: SPF, DKIM y DMARC en fase 1 —
ver [`CORREO.md`](CORREO.md).

**Cómo se revisó:** lectura del código y peticiones GET normales a los
sitios. No se explotó nada. Tres comprobaciones quedaron sin hacer por
limitaciones del entorno, y están al final.

---

## 1 · 🔴 CRÍTICO — El buscador de clientes es público

**Corregido — 2026-09-29.** Clave de servidor + OTP al correo registrado;
se retira la búsqueda antigua y el envío se inicia en un hilo daemon después del commit.

**`apps/project/api/platform/auth_platform/api/views.py:33`**

```python
class ClientSearchView(APIView):
    """GET /api/v1/clients/search/?documentNumber=xxx&birthDate=yyyy-mm-dd"""
    permission_classes = [AllowAny]
```

Sin autenticación, sin límite de peticiones, y devuelve —en palabras de su
propio docstring— *«datos en claro + form_id del formulario de insolvencia»*.

Por qué es grave, en concreto:

1. **La fecha de nacimiento no es un secreto: es un PIN de cuatro dígitos.**
   Un adulto tiene unas 25.000 fechas posibles. Sin throttling, eso se agota
   en minutos con un bucle.
2. **La cédula tampoco es secreta.** Está en contratos, facturas y radicados.
3. **Es un oráculo.** Contesta 404 si no existe y 200 si existe, así que
   sirve para confirmar si una persona concreta es cliente de insolvencia.
   Eso ya es información sensible, aunque no se llegue a sacar el resto.
4. Devuelve el **`form_id`**, que es la llave del resto del flujo.

Es el mismo error que ya se corrigió en el portal de procesos —la clave
derivada de la cédula— pero en otro endpoint y sin arreglar. **Un
identificador público no es una credencial.**

**Qué hacer.** Mitigación inmediata (una tarde): exigir autenticación y
poner throttling agresivo. Arreglo de fondo: el mismo flujo del portal,
identificación → código de un solo uso al correo registrado.

**Cómo comprobarlo.** Una petición sin credenciales devuelve 401/403, y la
número N dentro del minuto devuelve 429.

---

## 2 · 🔴 ALTO — La API es pública por defecto

**Corregido — 2026-09-29.** `IsAuthenticated` por defecto y `AllowAny` explícito
para formularios y contenido públicos, con lista blanca comprobada por un test
de todas las rutas API que exige 401/403 fuera de ella, también ante cuerpos vacíos.

**`app_core/settings.py:423`**

```python
'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
```

Es el inverso de seguro-por-defecto: **cada endpoint nuevo nace público** y
hay que acordarse de cerrarlo. Ya hay varios heredándolo sin decirlo
(`ContactCreateAPIView`, `PQRSModelCreateAPIView`, los dos `Register` de
Attlas), y uno con la deuda escrita en el propio código:

**`apps/project/api/platform/calculator/api/views.py:32`**

```python
permission_classes = [AllowAny]  # Ajustar según necesidades de seguridad
```

**Qué hacer.** `IsAuthenticated` por defecto, y `AllowAny` explícito solo
donde se decida. Hay que recorrer los endpoints existentes al cambiarlo: los
que hoy dependen del `AllowAny` heredado dejarán de responder, y algunos
—contacto, PQRS— sí deben seguir abiertos.

**Cómo comprobarlo.** Una prueba que recorra todas las rutas de la API sin
autenticar y exija que ninguna responda 200 salvo las de una lista blanca
escrita a mano. Así el próximo endpoint que nazca abierto rompe la prueba.

---

## 3 · 🟠 ALTO — El login de asesores no tiene freno

**Corregido — 2026-09-29.** Error único sin enumeración, fallos registrados
en django-axes y cupo de intentos por IP.

**`apps/project/api/platform/auth_platform/api/serializers.py:112`**

`AttlasInsolvencyAuthSerializer` sí verifica la contraseña del asesor. Pero
lanza `serializers.ValidationError` **sin emitir la señal
`user_login_failed`**, así que `django-axes` no se entera: no cuenta
intentos ni bloquea nada. Y sin throttling de DRF, tampoco hay otro límite.

Una contraseña de asesor es atacable sin límite, y las iniciales del asesor
—el campo `user`— son adivinables.

**Qué hacer.** Emitir `user_login_failed` en cada rama de fallo, o pasar la
autenticación por `authenticate()`. Añadir throttling al endpoint.

**Cómo comprobarlo.** N intentos fallidos seguidos y el N+1 rebota, aunque
la contraseña sea la correcta.

---

## Encontrados y corregidos durante la Fase 1

**Corregidos — 2026-09-29.**

- **IDOR del formulario/firma y `/clients/{id}`:** autenticación y comprobación
  de pertenencia al usuario antes de leer o modificar datos.
- **Firma por cédula:** ahora exige login; conocer la cédula no autoriza a firmar.
- **IP detrás del proxy de Vercel:** `X-Client-IP` solo se acepta con clave
  de servidor válida, para aplicar los cupos a la IP real.
- **Auditoría sin actor (2026-09-30):** `AuditlogMiddleware` iba *antes* que
  `AuthenticationMiddleware`, así que leía `request.user` cuando aún no existía
  y todo cambio quedaba en `LogEntry` sin usuario (solo la visibilidad de las
  notas lo esquivaba con un `set_actor` a mano). Ahora va detrás de la
  autenticación y del segundo factor (`OTPMiddleware`), el `set_actor` manual
  sobra y se quitó, y un test (`case_manager/tests/test_audit_actor.py`) fija
  el orden y comprueba el actor en un alta y una edición del gestor.
  **Los registros anteriores al cambio siguen sin actor**; no hay forma fiable
  de reconstruirlo.

---

## 4 · 🟡 MEDIO — CORS con comodín de subdominio

**Corregido — 2026-09-30.** `CORS_ALLOWED_ORIGINS` enumerado, sin regex.

Antes, `CORS_ALLOWED_ORIGIN_REGEXES` admitía cualquier subdominio de
`propensionesabogados.com`, `fundacionattlas.com` y `fundacionattlas.org`:
bastaba un subdominio abandonado apuntando a un servicio de terceros para que
alguien lo reclamase y hablase con la API desde un origen autorizado.

Ahora, en producción, solo estos seis (con y sin `www`):

```
https://geausa.propensionesabogados.com   https://www.geausa.propensionesabogados.com
https://fundacionattlas.com               https://www.fundacionattlas.com
https://fundacionattlas.org               https://www.fundacionattlas.org
```

Se puede cambiar sin tocar código con `CORS_ALLOWED_ORIGINS` en el `.env`
(lista separada por comas, con esquema y sin barra final; vacía o ausente =
la lista de arriba). En `DEBUG` son `http://localhost:3000` y
`http://0.0.0.0:3000`, ahora como orígenes normales (antes estaban puestos
como regex, que no era lo que se quería).

**Ojo al desplegar:** cualquier otro sitio que llame a la API desde el
navegador dejará de poder hacerlo. Si aparece uno legítimo, se añade a la
variable, no se vuelve al comodín.

Comprobado en `app_core/tests/test_security_headers.py`: un origen de la
lista recibe `Access-Control-Allow-Origin`; un subdominio cualquiera, un
`fundacionattlas.org.evil.com` y el mismo dominio en `http` no.

---

## 5 · 🟡 MEDIO — Sin CSP en los sitios Django

**Etapa 1 hecha — 2026-09-30: `Content-Security-Policy-Report-Only`.** Falta
la etapa 2 (hacerla efectiva).

Medido en las cabeceras de respuesta:

| Sitio | CSP |
|---|---|
| `propensionesabogados.com`, `geausa`, `atlas` (Django) | ⚠️ solo informe (pag); gea pendiente |
| `fundacionattlas.*`, `attlasconciliacion` (Next.js) | ✅ tienen |
| `fa.`, `correo.` | ❌ **ninguna cabecera de seguridad** |
| `sebasmd.com` | ❌ ninguna |

**Qué hay ahora (pag).** `django-csp` 4.0 (`csp.middleware.CSPMiddleware`),
con `CONTENT_SECURITY_POLICY_REPORT_ONLY` en `app_core/settings.py`. El
navegador **no bloquea nada**: manda un informe por cada cosa que bloquearía a
`POST /csp-report/` (`apps/common/utils/csp_report.py`), que lo apunta como
una línea de `WARNING` en `stderr.log` (logger `csp_report`), **sin guardar
nada en base de datos**, con un cupo de 60 informes por minuto y por IP, un
cuerpo máximo de 8 KiB, y sin apuntar query ni tokens de ruta.

La política se armó recorriendo las plantillas: Google Fonts, DataTables y
pdfmake (gestor, desde `cdn.datatables.net` y `cdn.jsdelivr.net`), reCAPTCHA
(formulario de contacto), el icono de Trace de la cabecera y Swagger/ReDoc
(`jsdelivr`, solo personal). Bootstrap, Bootstrap Icons, Swiper y AOS son
locales.

**Cómo ver qué rompería.** Dejarla unos días en producción y leer los
informes: `grep "CSP report-only" stderr.log`. Los que importan son los de
`script-src`/`script-src-elem` (scripts en línea) y cualquier origen que no
esté en la lista.

**Etapa 2: pasar a modo efectivo.** No se ha hecho y no es cambiar una
cabecera. Lo que hace falta:

1. **Nonces para los scripts en línea.** Hay 11 `<script>` sin `src`
   repartidos en 7 plantillas (`raw.html`, `partials/banner.html`, gestor:
   `base.html`, `case_form.html` —5—, `client_form.html`,
   `partials/portfolio.html`, y `signature/signature_widget.html`) y la política **no** lleva
   `'unsafe-inline'` en `script-src` a propósito: cada uno sale hoy en los
   informes. Para cada uno: o se mueve a un fichero estático, o se marca con
   `nonce="{{ request.csp_nonce }}"` (`django-csp` lo trae) y se añade
   `csp.constants.NONCE` a `script-src`. Con nonce, `'unsafe-inline'` deja de
   hacer falta y no debe añadirse nunca.
2. **Manejadores en línea** (`onclick="..."`, etc.): no llevan nonce y habría
   que pasarlos a `addEventListener`. En las plantillas no hay ninguno (se
   comprobó con búsqueda); si el JS los inyecta, aparecerían en los informes
   como `script-src-attr`.
3. **`style-src` con `'unsafe-inline'`.** Se dejó así porque hay atributos
   `style=` por todas partes y no admiten nonce. Quitarlo es una segunda
   limpieza, opcional.
4. **Los CDN con SRI** (`integrity=` + `crossorigin`): hecho (T3.7) para
   DataTables, pdfmake, Swagger UI y ReDoc, con versión fija; ver «Cerrado en la
   T3.7». Quedan las excepciones mutables (Google Fonts, reCAPTCHA).
5. Cuando los informes salgan limpios una semana: mover la configuración de
   `CONTENT_SECURITY_POLICY_REPORT_ONLY` a `CONTENT_SECURITY_POLICY` (la
   cabecera que bloquea). Se pueden tener las dos a la vez durante la
   transición.

**Pendiente:** el mismo trabajo en gea (Django), y `fa.`/`correo.`, que no son
Django y se arreglan en el servidor web.

---

## 6 · 🟢 Higiene de DNS

- **Sin DNSSEC** en los seis dominios. Sin él, el propio DNS es falsificable,
  y eso tumba de paso el SPF/DMARC recién puesto: de nada sirve una política
  si se puede mentir sobre el registro que la publica.
- **Sin CAA** en `propensionesabogados.com`, `fundacionattlas.com`,
  `tracecertificates.com` y `sebasmd.com`. Sin CAA, cualquier autoridad
  certificadora del mundo puede emitir un certificado para el dominio.

  ```
  CAA  @  0 issue "letsencrypt.org"
  CAA  @  0 iodef "mailto:info@propensionesabogados.com"
  ```

- **`sebasmoralesd.com` tiene sus dos NS en la misma IP** (`ns1` y `ns2`
  apuntan a `5.189.155.153`). Si ese VPS cae, el dominio deja de existir,
  correo incluido. No hay redundancia real.

---

## 7 · Pendiente de `CORREO.md`

- `sebasmd.com`: el SPF autoriza `190.90.160.170`, que es la IP del **web**.
  La de salida es `190.90.160.14`.
- `fundacionattlas.org` y `tracecertificates.com`: quitar el `+a`. Su
  registro `A` apunta a Vercel, cuya IP es compartida por todos sus clientes,
  así que ese `+a` autoriza a cualquiera de ellos a enviar como tuyo.
- Las fases 2 y 3 de DMARC, con su criterio de avance.
- `fa.org.propensionesabogados.com` parece un subdominio creado por error
  —un `fa.org` escrito donde iba `fa`—. Si no se usa, borrarlo: un
  subdominio olvidado con clave DKIM propia es justo lo que no conviene.

---

## 8 · Para Trace (DRF + Next.js), cuando arranque

El proyecto está pausado, así que sale gratis nacer con esto puesto.

**Backend**

1. `DEFAULT_PERMISSION_CLASSES = ['IsAuthenticated']` desde el primer commit.
2. `DEFAULT_THROTTLE_RATES` desde el primer commit, y con especial cuidado en
   cualquier endpoint que **busque personas**.
3. **JWT en cookie `HttpOnly` + `SameSite=Lax`, nunca en `localStorage`.** Un
   token en `localStorage` lo lee cualquier XSS; en cookie `HttpOnly`, no. Es
   la decisión que más cuesta revertir después.
4. Nunca un identificador público como credencial. Cédula + fecha de
   nacimiento no es autenticación: es una pregunta cuya respuesta está en los
   documentos del propio caso.
5. `django-axes` enganchado a **todos** los caminos de login, no solo al de
   Django.

**Frontend**

6. CORS con orígenes enumerados, sin comodines.
7. CSP sin `'unsafe-eval'` y sin `'unsafe-inline'` en `script-src`, con
   nonces. La CSP actual de los Next.js lleva los dos.
8. Claves de API nunca en `NEXT_PUBLIC_*`: eso viaja al navegador.

**Infra**

9. DNSSEC y CAA antes de publicar.
10. Mientras el dominio no envíe correo: `v=spf1 -all`, DMARC `p=reject` y MX
    nulo. Un dominio pausado es el blanco ideal, porque nadie vigila su correo.

---

## Clave servidor a servidor: `SERVER_KEY`

Un solo nombre de variable en los tres sistemas: **`SERVER_KEY`**. Protege la
API de Attlas (cabecera `X-Server-Key`), decide si se cree `X-Client-IP` y es
la clave del emisor `propensiones` ante gea (cabecera `X-Issuer-Key`). Mínimo
32 caracteres sin `DEBUG` (system check `utils.E001`). Las cabeceras HTTP no
cambian.

Las variables viejas `ATTLAS_SERVER_KEY` y `GEA_ISSUER_KEY_PROPENSIONES` se
siguen leyendo solo si falta `SERVER_KEY`, y `manage.py check` avisa
(`utils.W002`). Se retirarán.

**Despliegue:** poner `SERVER_KEY` con el mismo valor en el `.env` de pag, el
`.env` de gea y Vercel (fundacionattlas.org); reiniciar/redesplegar los tres y
comprobar que `check` ya no avisa; después borrar las variables viejas.

---

## Lo que no se pudo comprobar

Tres cosas quedaron fuera por el entorno desde el que se revisó, no porque
estén bien:

| Qué | Por qué | Cómo comprobarlo |
|---|---|---|
| **Puertos abiertos** | Salida solo por HTTPS | `nmap -Pn -sV -p- 190.90.160.103 190.90.160.170 5.189.155.153` |
| **Certificados TLS** | Proxy con interceptación TLS: se ve el suyo | [SSL Labs](https://www.ssllabs.com/ssltest/) |
| **`sebasmoralesd.com`** | Reseteó la conexión a mitad de la revisión | Repetir desde fuera |

Lo que preocupa del escaneo de puertos es MySQL (3306) o Redis (6379)
escuchando en público.

---

## Lo que sí está bien

Para no leer solo la lista de defectos:

- `.env` y `.git/config` devuelven 403 en todo el cPanel.
- No hay listados de directorios ni ficheros de respaldo expuestos.
- Las cabeceras de `propensionesabogados.com` traen HSTS con `preload`,
  `X-Frame-Options`, `nosniff` y `Referrer-Policy`.
- Las cookies de sesión y CSRF van `Secure` y `HttpOnly`.
- El sitio ya publica `/.well-known/security.txt`.
- Los sitios Next.js traen CSP y `Permissions-Policy`.

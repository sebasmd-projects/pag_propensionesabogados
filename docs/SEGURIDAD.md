# Plan de seguridad — seguimiento

Hallazgos de la revisión del **25 de septiembre de 2026**. La Fase 1 queda
cerrada el **29 de septiembre de 2026**: los puntos 1, 2 y 3 están corregidos.
El **30 de septiembre de 2026** se corrige el 4 (CORS) y el 5 queda en su
primera etapa (CSP en modo solo informe). Se conserva el diagnóstico original
como referencia; los hallazgos 6 a 8 siguen pendientes.

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
4. **Los CDN con SRI** (`integrity=` + `crossorigin`) para DataTables y
   pdfmake, o traerlos a `public/staticfiles` y quitar los dos orígenes.
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

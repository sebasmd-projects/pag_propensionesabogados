# Plan de seguridad — pendiente de aplicar

Hallazgos de la revisión del **25 de septiembre de 2026**. **Nada de esto
está aplicado todavía**: se aparca hasta terminar la integración de
`gea_module_0`, para no mezclar cambios de seguridad con una migración a
medias y quedarse sin saber qué rompió qué.

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

## 4 · 🟡 MEDIO — CORS con comodín de subdominio

**`app_core/settings.py:455`**

```python
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://[A-Za-z0-9-]+\.propensionesabogados\.com$',
    ...
]
```

Cualquier subdominio, presente o futuro, puede llamar a la API desde el
navegador. Hay nueve subdominios; basta que uno quede abandonado apuntando a
un servicio de terceros para que alguien lo reclame y hable con la API desde
un origen que tú autorizas.

**Qué hacer.** Enumerar los orígenes reales en `CORS_ALLOWED_ORIGINS`. Son
pocos y cambian poco.

---

## 5 · 🟡 MEDIO — Sin CSP en los sitios Django

Medido en las cabeceras de respuesta:

| Sitio | CSP |
|---|---|
| `propensionesabogados.com`, `geausa`, `atlas` (Django) | ❌ ninguna |
| `fundacionattlas.*`, `attlasconciliacion` (Next.js) | ✅ tienen |
| `fa.`, `correo.` | ❌ **ninguna cabecera de seguridad** |
| `sebasmd.com` | ❌ ninguna |

Lo llamativo es el contraste: los Next.js ya traen una CSP decente y los
Django no traen ninguna. Es `django-csp`, media tarde.

Empezar en `Content-Security-Policy-Report-Only` para ver qué rompería antes
de hacerla efectiva. La del proyecto tiene CDN de por medio —DataTables,
pdfmake— así que la política tiene que contemplarlos.

**`fa.` y `correo.` no son Django**: esos se arreglan en el servidor web.

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

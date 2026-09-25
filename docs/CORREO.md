# Autenticación del correo: SPF, DKIM y DMARC

Estado comprobado en el DNS público el **25 de septiembre de 2026**, con SPF
y DMARC ya instalados y en **fase 1** (`p=none`). Si lees esto mucho después,
vuelve a comprobarlo antes de tocar nada: son registros que cambian fuera del
repositorio y este fichero no se entera.

---

## Por qué esto importa

Hoy cualquiera puede mandar un correo que diga venir de
`director@propensionesabogados.com` y llegará a la bandeja de entrada. No hace
falta entrar en ningún sitio ni robar ninguna contraseña: el `From:` de un
correo es un campo de texto que escribe quien envía, igual que el remitente de
un sobre de papel.

Para un despacho de abogados eso no es un problema de imagen. Es un correo
falso que pide una consignación a nombre de un proceso real, o que manda un
«paz y salvo» adjunto a un cliente que lo estaba esperando.

### Las tres piezas, y cuál falta

| | Qué hace | Estado |
|---|---|---|
| **SPF** | Dice qué servidores pueden enviar en nombre del dominio. Valida el remitente del **sobre**, no el `From:` que ve la persona. | Falta en casi todo |
| **DKIM** | Firma cada correo con una clave del dominio. Demuestra que el mensaje no se alteró. | ✅ Puesto en todos |
| **DMARC** | Exige que SPF o DKIM **alineen** con el dominio del `From:` visible, y le dice al receptor qué hacer si no. | **Falta en todo** |

El malentendido que hay que deshacer: **tener DKIM no protege de nada por sí
solo.** DKIM firma, pero no obliga a nadie a comprobar la firma. Si llega un
correo sin firma, o con la firma rota, el receptor no tiene ninguna
instrucción sobre qué hacer con él, así que lo entrega.

DMARC es la única pieza que cierra el agujero, porque es la única que dice
«si no alinea, recházalo». Por eso el orden de trabajo es: SPF primero
(porque DMARC lo necesita), DMARC después, y DKIM ya está.

---

## Estado actual

**La IP del correo no es la del web.** Es el error que costó dos vueltas:
`190.90.160.103` es el servidor web y `190.90.160.109` el de correo saliente.
Un SPF escrito mirando el registro `A` autoriza la máquina equivocada, y eso
no se nota hasta la fase 3 --con `p=none` no rechaza nadie--, momento en el
que empieza a fallar el correo propio.

```
190.90.160.103  →  cpanel2-co.conexcol.net        (web)
190.90.160.109  →  smtp.cpanel2-co.conexcol.net   (correo saliente)  ← esta
190.90.160.170  →  cpanel4-co.conexcol.net        (web, otra cuenta)
190.90.160.14   →  smtp.cpanel4-co.conexcol.net   (correo saliente) ← y esta
```

La forma fiable de saberlo es el `PTR`, no el `A`:

```bash
dig +short -x 190.90.160.109    # smtp.cpanel2-co.conexcol.net.
```

O más simple: dejar que lo calcule **cPanel → Email Deliverability → Repair**,
que sí conoce la IP de salida de su propio servidor.

### Los remitentes

Cada subdominio con clave en `default._domainkey` es un remitente
independiente para cPanel. La lista completa **no se puede deducir del DNS**:
sale de **cPanel → Email Deliverability**, y por eso aparecieron cuatro que no
estaban en la primera pasada.

| Remitente | Servidor | Estado (25/09/2026) |
|---|---|---|
| `propensionesabogados.com` | cpanel2 · `.109` | ✅ SPF + DMARC con `rua` |
| `fundacionattlas.com` | cpanel2 · `.109` | ✅ SPF + DMARC con `rua` |
| `atlas`, `attlasconciliacion`, `correo`, `fa`, `fa.org`, `gea`, `geausa`, `rt`, `tc` (subdominios) | cpanel2 · `.109` | ✅ SPF propio; DMARC heredado |
| `procesodeinsolvencia.com` | cpanel4 · `.14` | ✅ SPF + DMARC con `rua` |
| `sebasmd.com` | cpanel4 · `.14` | ⚠️ SPF con la IP del web |
| `fundacionattlas.org` | Vercel | ⚠️ `+a` autoriza Vercel entero |
| `tracecertificates.com` | Vercel | ⚠️ `+a` autoriza Vercel entero |

`fa.org.propensionesabogados.com` tiene pinta de subdominio creado por error
--parece un `fa.org` escrito donde iba `fa`--. Un subdominio olvidado con
clave DKIM propia es justo lo que no conviene tener; si no se usa, se borra.

**Tres reglas de herencia, que es donde se cuela el error:**

- **SPF no se hereda.** `atlas.propensionesabogados.com` no usa el SPF de la
  raíz. Sin uno propio, un correo con `From: algo@atlas.…` no tiene SPF que
  validar y solo le queda el DKIM.
- **DMARC sí se hereda, pero solo si el subdominio no tiene el suyo.** El
  `Repair` de cPanel crea un `_dmarc` en **cada** subdominio, y eso anula el
  `sp=` de la raíz: al llegar a la fase 3, los subdominios se quedarían en
  `p=none` con el registro de la raíz viéndose perfecto. Se borran los
  `_dmarc` de subdominio y se deja solo el de la raíz.
- **`sp=` es un campo aparte de `p=`.** cPanel genera `p=none;sp=none;`, con
  los dos explícitos. En la fase 3 hay que cambiar **los dos**.

### Cuidado con `+a` en dominios alojados fuera

`+a` autoriza a quien esté en el registro `A`. En un cPanel propio eso es la
misma máquina y no pasa nada; en un alojamiento compartido como Vercel, el
`A` es una IP **anycast que comparten todos sus clientes**, así que `+a`
autoriza a cualquiera de ellos a enviar como tuyo.

Le pasa a `fundacionattlas.org` y a `tracecertificates.com`: su web se movió a
Vercel y el `A` dejó de ser el cPanel. El botón `Repair` lo añade sin mirar a
dónde apunta, así que en esos dos hay que quitar el `+a` a mano.

---

## Los registros

### Paso 1 · SPF

Va como TXT. **Puede haber varios TXT en el mismo nombre** —el
`google-site-verification` se queda donde está—, pero **no puede haber dos
SPF**: si hay dos, los receptores tratan el dominio como si no tuviera
ninguno.

En la raíz de cada dominio y en cada subdominio que envíe. El Zone Editor de
cPanel **no acepta `@`**: hay que escribir el nombre completo **con punto
final**, o cPanel le añade el dominio otra vez y el registro acaba en
`propensionesabogados.com.propensionesabogados.com` sin dar ningún error.

```
Nombre:  propensionesabogados.com.          ← el punto final importa
Tipo:    TXT
TTL:     14400
Valor:   v=spf1 +mx +ip4:190.90.160.109 ~all
```

El valor va **sin comillas**: cPanel las pone al guardar, y si se escriben a
mano acaban dobles y el registro deja de ser un SPF válido.

En cpanel4 (`sebasmd.com`, `procesodeinsolvencia.com`) la IP es
`190.90.160.14`.

`~all` es *softfail*: «lo que no venga de ahí es sospechoso, pero entrégalo».
Se empieza así a propósito, y se sube a `-all` cuando DMARC lleve un mes
limpio. Poner `-all` de entrada, sin saber todavía quién envía, es la forma
más rápida de que dejen de llegar correos legítimos sin que nadie sepa por
qué.

### Paso 2 · DMARC

Antes de nada, **crea el buzón `dmarc@` de cada dominio**. Si no existe, los
informes se pierden y la fase de inventario no sirve para nada. Y escribe la
dirección entera: un `rua=mailto:dmarc@<el-dominio>` copiado de una plantilla
sin sustituir no es una dirección válida, así que el registro se ve correcto,
pasa cualquier validador, y no recoge nada. Pasó.

Existen: `dmarc@propensionesabogados.com`, `dmarc@fundacionattlas.com`,
`dmarc@sebasmd.com`, `dmarc@procesodeinsolvencia.com`.

Esto va por fases. No es burocracia: cada fase te da la información que
necesitas para no romper nada en la siguiente.

**Fase 1 — inventario (semanas 1 y 2).** No bloquea absolutamente nada; solo
pide informes.

```
Nombre:  _dmarc
Tipo:    TXT
TTL:     14400
Valor:   v=DMARC1; p=none; rua=mailto:dmarc@propensionesabogados.com; fo=1; adkim=r; aspf=r
```

**Fase 2 — cuarentena (semanas 3 y 4).** Lo suplantado va a Spam en vez de a
la bandeja. Pasa a esta fase solo cuando los informes lleven una semana sin
remitentes legítimos fallando.

```
Valor:   v=DMARC1; p=quarantine; pct=100; rua=mailto:dmarc@propensionesabogados.com; fo=1; adkim=r; aspf=r
```

**Fase 3 — rechazo (a partir de la semana 5).** Lo suplantado se rechaza en el
borde: no llega ni a Spam.

```
Valor:   v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s; rua=mailto:dmarc@propensionesabogados.com; fo=1
```

**`p=` y `sp=` son dos campos.** cPanel genera los dos explícitos
(`p=none;sp=none;`), así que cambiar solo `p=` deja los nueve subdominios sin
proteger con el registro de la raíz viéndose perfecto. Hay que cambiar los dos.

`adkim=s` y `aspf=s` exigen alineación **estricta**: el dominio de la firma
tiene que ser exactamente el del `From:`, no uno de su familia.

Repite los tres pasos en cada dominio. Los subdominios no llevan `_dmarc`
propio: lo heredan, y por eso se borran los que crea `Repair`.

**Antes de la fase 3, sube también el SPF de `~all` a `-all`.** Con `~all` un
receptor puede entregar igual lo que no venga de tu servidor; es el par que
cierra la puerta.

### Paso 3 · Subdominios que NO envían

Para que no se puedan usar como remitente:

```
Nombre:  <subdominio>
Tipo:    TXT
Valor:   v=spf1 -all
```

---

## Antes de endurecer: la comprobación que no te puedes saltar

En el `.env` de producción:

```bash
grep DJANGO_EMAIL_HOST .env
```

- Si es `localhost`, `mail.propensionesabogados.com` o la IP del servidor →
  el correo de la plataforma sale por el mismo sitio que el resto y queda
  alineado solo. Los registros de arriba bastan.
- Si es un SMTP externo (Gmail, SendGrid, Mailgun, Zoho…) → **todo el correo
  que manda la aplicación** (los códigos de acceso del portal, los avisos de
  novedades a los clientes, el segundo factor del gestor) empezará a fallar
  DMARC en cuanto pongas `quarantine`. Ese proveedor hay que añadirlo al SPF
  con su `include:` y configurarle DKIM con dominio propio antes de pasar de
  fase.

La fase `p=none` existe justamente para descubrir esto sin romper nada.

---

## Cómo aplicarlo en cPanel

**SPF y DKIM** tienen camino corto: **cPanel → Email Deliverability**. Lista
los dominios, marca en rojo lo que falta y con **Repair** instala los dos
registros correctos. Hazlo dominio por dominio; los subdominios salen en la
misma lista.

**DMARC no lo genera cPanel.** Ese va a mano: **Zone Editor → Manage →
Add Record → TXT**, con el nombre `_dmarc`.

Propagación: entre 15 minutos y 4 horas con el TTL de 14400 que tiene la zona.

---

## Comprobar que quedó bien

```bash
dig +short TXT propensionesabogados.com
dig +short TXT _dmarc.propensionesabogados.com
dig +short TXT default._domainkey.propensionesabogados.com
```

Sin `dig` a mano, [MXToolbox](https://mxtoolbox.com/dmarc.aspx) o
[dmarcian](https://dmarcian.com/domain-checker/).

La prueba de verdad es mandar un correo desde una cuenta del dominio a
`check-auth@verifier.port25.com`: responde con un informe línea a línea. Lo
que tiene que salir:

```
SPF check:          pass
DKIM check:         pass
DMARC check:        pass
```

---

## Cómo leer los informes DMARC

Llegan a diario, en XML comprimido, uno por cada proveedor que recibe correo
tuyo (Google, Microsoft, Yahoo…). A mano no se leen: súbelos a
[dmarcian](https://dmarcian.com/) o a [Postmark DMARC](https://dmarc.postmarkapp.com/),
que son gratis para un volumen como el del despacho.

Lo que se mira, en este orden:

1. **Remitentes que no reconoces con `dkim=pass`.** Es lo más preocupante:
   alguien con una clave válida del dominio. Casi siempre es un servicio
   contratado y olvidado.
2. **Remitentes que reconoces fallando.** Son los que hay que arreglar
   —añadir al SPF, configurarles DKIM— antes de pasar de fase. Si pasas con
   estos fallando, dejan de llegar correos legítimos.
3. **Volumen de fallos desde IPs desconocidas.** Eso es la suplantación que
   estás tapando. No hay nada que arreglar: es lo que `p=reject` va a
   rechazar.

Regla para avanzar de fase: **una semana entera sin nada en el punto 2.**

---

## Lo que esto no resuelve

- **Dominios parecidos** (`propensiones-abogados.com`,
  `propensionesabogado.com`, `propensionesabogados.co`). DMARC solo protege el
  dominio exacto. Ahí lo que toca es registrar las variantes obvias y vigilar
  los registros nuevos.
- **Cuentas comprometidas.** Si alguien entra con la contraseña de una cuenta
  real, el correo sale firmado y alineado, y DMARC lo da por bueno —porque lo
  es—. Eso se cubre con segundo factor en el correo, no con DNS.
- **El contenido.** DMARC dice quién envía, no si lo que dice es verdad.

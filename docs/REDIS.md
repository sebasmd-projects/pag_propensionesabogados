# Redis compartido para pag (el mismo Redis del VPS que usa gea)

Por qué: los cupos de intentos de este sitio —acceso por código al correo,
recuperación de contraseña, registro, contacto, PQRS, portal del cliente— viven
en cache. Sin `REDIS_URL`, Django usa `LocMemCache`, que es **por proceso**: con
N workers el límite real es N veces mayor y se reinicia en cada despliegue.
Con `REDIS_URL` el contador es uno solo.

El servidor web (cPanel) no admite Redis, así que se reutiliza el Redis que ya
corre en el VPS para gea. **No se monta otro: se le añade un usuario.** Todo lo
que sigue son los pasos de **quien administra el VPS y el cPanel de pag**; el
código ya está listo y, mientras `REDIS_URL` esté vacía, se comporta como hasta
ahora.

> Los valores entre `<…>` son marcadores: ni este documento ni el repositorio
> llevan hosts, IPs ni contraseñas reales. Cópialos de la instalación de gea
> (`deploy/REDIS.md` de ese proyecto, pasos 0 a 5), que es la que manda.

## Qué NO se hace

| No | Por qué |
|---|---|
| Usar el usuario `gea` ni su contraseña | Un fallo o una fuga de un sitio no debe dar acceso al otro. Cada sitio, su usuario |
| Dar al usuario `~*` | Las ACL de Redis **no se acotan por base de datos**: `~*` ve las claves de gea. Quien aísla es el patrón de claves |
| Abrir otro puerto o quitar el TLS | El tráfico sale a internet; es el mismo puerto TLS con la misma CA |
| Mover las sesiones a la cache | Siguen en la base de datos: un Redis caído no cierra la sesión de nadie |

## Qué hace el código (ya está en la rama)

- `REDIS_URL` vacía → `LocMemCache`, como antes.
- `REDIS_URL` puesta → `django-redis` con `IGNORE_EXCEPTIONS` (un Redis caído
  no tumba el sitio), `KEY_PREFIX = REDIS_KEY_PREFIX` (por defecto **`pag`**) y
  tiempos de conexión de 3 s (`REDIS_CONNECT_TIMEOUT`, `REDIS_TIMEOUT`).
- Todas las claves empiezan por `pag:`, que es lo único que el usuario ACL de
  este sitio puede tocar.
- `django-redis==7.0.0` y `redis==8.1.0` están en `pyproject.toml`, `uv.lock` y
  `requirements.txt` (en cPanel se instala con `pip`, no con `uv`).

## Paso 1. Datos que necesitas

| Dato | Dónde sale |
|---|---|
| `<REDIS_HOST>` y `<PUERTO>` | Los mismos que usa gea en su `REDIS_URL` |
| `ca.crt` | La CA propia del VPS (la de gea). **Solo `ca.crt`**: nunca `ca.key` ni `redis.key` |
| `<IP_SALIDA_PAG>` | La IP de **salida** del hosting de pag. Desde SSH en el cPanel de pag: `curl -s https://ifconfig.io` |
| `<N>` | Una base de datos libre. gea usa la 0 (cache) y, si tiene cola de tareas, la 1. Propuesta: **2**. Compruébalo en el VPS: `redis-cli … INFO keyspace` |

**Por qué una base propia (`/<N>`) y no la 0.** `manage.py clear_cache` hace
`FLUSHDB`, que vacía **toda la base**, no solo las claves `pag:*`. En la base 0
vaciaría también los contadores de gea. En una base propia solo vacía los de pag.

**Firewall.** Si el hosting de pag es el mismo que el de gea y la IP de salida
coincide, esa IP ya está autorizada en `DOCKER-USER` y no hay nada que hacer.
Si es distinta, hay que **añadirla** antes del `DROP`, como en el paso 5 de gea:

```bash
sudo iptables -I DOCKER-USER -p tcp --dport <PUERTO> -s <IP_SALIDA_PAG> -j RETURN
sudo netfilter-persistent save
sudo iptables -L DOCKER-USER -n --line-numbers   # el RETURN, antes que el DROP
```

## Paso 2. El usuario ACL de pag, en el VPS

La contraseña **no** es la de gea. Genérala y guarda el hash:

```bash
openssl rand -base64 36                       # la contraseña de pag; guárdala
printf '%s' 'LA_CONTRASEÑA' | sha256sum       # 64 hex en minúscula: este va al fichero
```

En el `redis.conf` del VPS (el mismo fichero donde están `user default off`,
`user health …` y `user gea …`), **añade una línea nueva y no toques las otras**:

```conf
user pag on #<SHA256_DE_LA_CONTRASEÑA_DE_PAG> ~pag:* +@read +@write +@keyspace -@dangerous +flushdb +select
```

Qué hace cada trozo, para que nadie lo «simplifique»:

| Trozo | Por qué |
|---|---|
| `#<sha256>` | El hash, no la contraseña. Con la contraseña en claro Redis **no arranca** |
| `~pag:*` | Solo claves con el prefijo de pag. No ve ni toca `gea:*` ni `celery*` |
| `+@read +@write +@keyspace` | `GET`, `SET`, `INCR`, `EXPIRE`, `DEL`… lo que usa la cache |
| `-@dangerous` | Sin `KEYS`, `CONFIG`, `SHUTDOWN`, `FLUSHALL`… |
| `+flushdb` | Lo usa `manage.py clear_cache`. **Va después de `-@dangerous`**: las reglas se aplican de izquierda a derecha y al revés lo revoca |
| `+select` | **Imprescindible con una base distinta de la 0.** `redis-py` hace `SELECT <N>` al conectar. Sin este permiso, **toda** operación falla con `NOPERM` y, por `IGNORE_EXCEPTIONS`, no da error: la cache devuelve `None` y los cupos dejan de contar sin ruido. Comprobado contra un Redis real |

Aplícalo recreando el contenedor (el nombre y la ruta son los de la instalación
de gea; ajusta si difieren):

```bash
cd /opt/gea-redis && sudo docker compose up -d --force-recreate
sudo docker compose ps          # tiene que quedar «healthy»
```

> Durante esos segundos Redis no responde **también para gea**: sus cupos fallan
> cerrados (rechazan) hasta que vuelve. Hazlo en un momento tranquilo. Si el
> contenedor entra en bucle, el motivo está en `sudo docker logs --tail 20
> <contenedor>` (casi siempre, el hash mal pegado).

## Paso 3. Comprobar el aislamiento, desde el VPS

Con el cliente del propio contenedor (mismas opciones TLS que en la instalación
de gea):

```bash
R="sudo docker exec <contenedor> redis-cli --tls --cacert /tls/ca.crt -p <PUERTO> --user pag --pass 'LA_CONTRASEÑA_DE_PAG' --no-auth-warning"

$R -n <N> SET pag:ping ok        # -> OK
$R -n <N> SET gea:ping ok        # -> NOPERM  (no puede tocar lo de gea)
$R -n <N> FLUSHALL               # -> NOPERM
$R -n <N> CONFIG GET maxmemory   # -> NOPERM
```

Y que gea sigue sin ver a pag: con el usuario de gea, `GET pag:ping` tiene que
dar `NOPERM`. Si alguno de estos no sale como se indica, **no sigas**.

## Paso 4. La CA y el `.env`, en el cPanel de pag

1. Copia **solo `ca.crt`** del VPS al home del cPanel de pag
   (`/home/<usuario_cpanel>/redis-ca.crt`), permisos `600`.
2. En el `.env` de producción de pag (nunca en el repositorio):

```
REDIS_URL=rediss://pag:<CONTRASEÑA_DE_PAG>@<REDIS_HOST>:<PUERTO>/<N>?ssl_cert_reqs=required&ssl_ca_certs=/home/<usuario_cpanel>/redis-ca.crt
REDIS_KEY_PREFIX=pag
REDIS_CONNECT_TIMEOUT=3
REDIS_TIMEOUT=3
```

`ssl_cert_reqs=required` **junto con** `ssl_ca_certs` es lo que hace que el TLS
sirva de algo. Si la contraseña lleva caracteres especiales (`/`, `+`, `=`,
`@`), codifícalos en la URL (`%2F`, `%2B`, `%3D`, `%40`).

3. Instala las dependencias (en cPanel es `pip`): *Setup Python App* → la
   aplicación → **Run Pip Install** sobre `requirements.txt`, o por SSH con el
   entorno virtual que muestra esa pantalla: `pip install -r requirements.txt`.
   Comprueba antes que llegó al fichero: `python manage.py check_requirements`.

## Paso 5. Comprobar y reiniciar

```bash
python manage.py check_cache
```

Reinicia la aplicación (*Setup Python App* → **Restart**) y vuelve a ejecutar
`check_cache` y `python manage.py check_security`. Lo que tiene que salir:

```
1. Backend            django_redis.cache.RedisCache  (servidor: rediss://***@<host>…)
2. Ida y vuelta       Escribe y lee correctamente.
3. Contador (incr)    Cuenta bien: 1, 2.
4. Caducidad          Las claves caducan.
5. Compartida         El otro proceso la ve. La cache es compartida.
```

y en `check_security`: «Cache compartida: los límites cuentan de verdad» y «Redis
por TLS». La prueba que decide es la 5: escribe una clave y la lee **desde otro
proceso**.

Si la 2 dice que se escribió y volvió `None`, es la señal de «Redis inalcanzable
o sin permiso»: `IGNORE_EXCEPTIONS` esconde el error. `check_cache` lo
diagnostica por capas (CA → DNS → TCP → TLS → usuario/contraseña). Los casos
habituales: el cortafuegos no lleva la IP de salida de pag (capa 2); la CA no es
la que firmó el certificado (capa 3); contraseña mal copiada o **falta `+select`**
con una base distinta de la 0 (capa 4: `no permissions to run the 'select'
command`).

## Qué pasa si Redis se cae

La aplicación sigue en pie (nada de 500), pero **los cupos no se pueden contar**
y cada uno decide qué hacer. Es una decisión por formulario, escrita en su código:

| Cupo | Con Redis caído |
|---|---|
| Acceso por código al correo, recuperación de contraseña | Se rechaza (falla cerrado) |
| Registro, contacto (portada y API) | Se rechaza (falla cerrado) |
| PQRS | Pasa (falla abierto, a propósito: es un canal de radicación; ver `pqrs_by_ip`) |
| Fallos del portal del cliente | El fallo cuenta como el último permitido: esa IP descansa |
| Contraseña (axes), sesiones | No dependen de la cache: siguen funcionando |

Cada caso queda en el log como `La cache no responde…`. Si en producción ves esa
línea, `check_cache` dice por qué.

## Volver atrás

Quita `REDIS_URL` del `.env` y reinicia: Django vuelve a `LocMemCache` sin tocar
código. En el VPS, el usuario `pag` puede quedarse en el `redis.conf` (sin uso no
abre nada) o retirarse recreando el contenedor.

## Rotar la contraseña

Cambia el hash de la línea `user pag` en el `redis.conf`, recrea el contenedor
(`up -d --force-recreate`) y actualiza `REDIS_URL` en el `.env` del cPanel, en ese
orden y con minutos de margen: en medio, los cupos fallan según la tabla de arriba.

## Una advertencia sobre la memoria

El Redis de gea tiene `maxmemory-policy allkeys-lru`: si algún día se llena, expulsa
claves de **cualquiera** de los dos sitios, también contadores a mitad de ventana.
Los contadores ocupan muy poco; la señal de alarma sería `DBSIZE` creciendo sin
parar en la base de pag.

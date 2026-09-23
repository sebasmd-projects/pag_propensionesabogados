"""
Enganches de `django-axes`, para que el freno al tanteo no sea un autobloqueo.

`axes` viene con valores por defecto deliberadamente severos: tres fallos y
bloqueo **permanente** (`AXES_COOLOFF_TIME = None`) **por IP** y solo por IP.
En un despacho cuyo personal comparte la salida a internet, eso significa que
una persona tecleando mal su contrasena tres veces deja fuera a todo el mundo
hasta que alguien entre a la base a mano. Y como `AXES_RESET_ON_SUCCESS`
tambien viene en `False`, los fallos no se olvidan nunca.

Aqui viven las tres piezas que `settings.py` necesita para arreglarlo sin
duplicar nada de lo que el proyecto ya tiene:

1. **Una sola respuesta a «de donde viene esto».** `axes` trae su propia
   deteccion de IP; el proyecto ya tiene la suya en `client_ip`, que no se
   cree `X-Forwarded-For` salvo que se declare un proxy. Hoy coinciden por
   casualidad; el dia que se declare uno, el bloqueo de acceso caeria sobre
   una direccion distinta de la que ve el resto de la aplicacion.

2. **Que la lista blanca sirva tambien para el acceso.** `WhiteListedIPModel`
   es el remedio cuando alguien queda bloqueado por error, y `axes` no la
   conoce: anadir la IP levantaba la mitigacion anti-escaneo y dejaba el
   acceso igual de cerrado.

3. **Que `axes` se entere de _quien_ falla.** Busca un campo `username` en el
   POST, pero el acceso es un asistente de `formtools` y su campo se llama
   `auth-username`. Sin esto, cada fallo se guarda con `username=None`,
   y eso tiene dos consecuencias que se ven en las pruebas:

   * el bloqueo por la pareja (IP, usuario) **degrada en silencio** a bloqueo
     por IP, porque el usuario siempre es el mismo: nadie;
   * y al reves, quien luego llega con la contrasena correcta se consulta como
     (IP, «ana»), que no tiene ni un fallo apuntado, asi que **entra pese al
     bloqueo**.

Nada de esto convierte el bloqueo por IP en un control de seguridad: sigue
siendo un freno al tanteo, y ante la duda vale mas dejar entrar a alguien
lento que dejar fuera al despacho.
"""

import logging

from .client_ip import get_client_ip, is_whitelisted

logger = logging.getLogger(__name__)

#: El acceso vive en un asistente de formtools, que prefija cada campo con el
#: nombre de **su paso**: el de contrasena es `auth`. `username` a secas queda
#: para cualquier otro formulario que llame a `authenticate()`.
USERNAME_FIELDS = ('auth-username', 'username')


def client_ip(request) -> str:
    """IP para `AXES_CLIENT_IP_CALLABLE`."""
    return get_client_ip(request)


def is_lockout_exempt(request, credentials=None) -> bool:
    """
    Si esta peticion de acceso nunca debe quedar bloqueada.

    Solo mira la lista blanca de IP. No se exime al personal interno: en el
    acceso todavia no hay sesion, asi que quien lo intenta es siempre anonimo
    y eximir por `is_staff` aqui no significaria nada.
    """
    try:
        return is_whitelisted(client_ip(request))
    except Exception:                                       # noqa: BLE001
        # La lista blanca es un remedio de disponibilidad. Si falla al
        # consultarla, lo correcto no es eximir a todo el mundo del freno al
        # tanteo: se sigue el camino normal.
        logger.warning(
            'No se pudo consultar la lista blanca; se aplica el bloqueo.'
        )
        return False


def username(request, credentials=None) -> str:
    """
    Quien esta intentando entrar, para `AXES_USERNAME_CALLABLE`.

    Se normaliza a minusculas y sin espacios para que «Ana» y « ana » cuenten
    como el mismo intento y no abran tres cuentas atras distintas.
    """
    value = ''

    if credentials:
        value = credentials.get('username') or ''

    if not value and request is not None:
        post = getattr(request, 'POST', None)

        if post is not None:
            for field in USERNAME_FIELDS:
                value = post.get(field) or ''

                if value:
                    break

    return value.strip().casefold()

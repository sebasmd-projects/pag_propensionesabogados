"""
Un cubo de intentos por ventana de tiempo, para formularios publicos.

Que problema resuelve
---------------------
El portal de consulta ya tenia su contador (`case_manager.attempts`), atado a
su propio bloqueo por IP. El acceso por codigo al correo necesita otros dos
que no encajan ahi:

* **cuantos codigos se mandan a un buzon.** El cupo tiene que agotarse aunque
  quien los pida cambie de direccion en cada intento, porque lo que se protege
  no es el servidor sino el buzon de un tercero: si la IP formara parte de la
  llave, rotarla seria el bypass.
* **cuantos se piden desde una conexion**, que si va por IP.

Por que el fallo es **cerrado**
-------------------------------
Si la cache no responde, se rechaza. La tentacion es la contraria --«un
formulario que deja de funcionar porque la cache esta caida es una denegacion
de servicio que nos hacemos solos»-- y vale cuando el limite evita una
molestia pasajera. Aqui el limite **es** el control: sin el, pedir codigos
sale gratis y se puede llenar el buzon de cualquiera. Una molestia se acaba
cuando se acaba la averia; un buzon inundado, no.

Como se nota que la cache no responde
-------------------------------------
No con un `try/except`. Un backend configurado con `IGNORE_EXCEPTIONS`
--lo normal para que un Redis caido no tumbe el sitio-- **devuelve `None` en
vez de lanzar**, asi que el manejador no se ejecutaria nunca: `None or 0` es
`0`, y `0 < limite`. Lo que si distingue una cache viva es que `incr`
devuelva un numero, y por eso se incrementa antes de comparar.
"""

import hashlib
import logging

from django.core.cache import cache

from .client_ip import get_client_ip

logger = logging.getLogger(__name__)


class RateLimit:
    """
    Cuantos intentos caben, y de quien.

    Args:
        name: identifica al formulario. Dos con el mismo nombre comparten cupo.
        limit: intentos por ventana.
        window: duracion de la ventana, en segundos.
    """

    def __init__(self, name: str, *, limit: int, window: int):
        self.name = name
        self.limit = limit
        self.window = window

    def key_for(self, request, scope=None) -> str:
        """
        Por IP salvo que se diga otra cosa.

        Sin `scope`, el cubo es de la direccion y no de la sesion: la sesion la
        controla quien ataca, y tirar la cookie para empezar de cero es una
        linea de script.

        Con `scope`, el cubo es de eso --un correo, un identificador-- y la IP
        no entra. Se guarda **hasheado**: una llave de cache es un sitio donde
        nadie espera encontrar datos personales, y el hash conserva lo unico
        que hace falta, que dos valores iguales caigan en el mismo cubo.
        """
        if scope is None:
            scope = get_client_ip(request) or 'desconocida'
        else:
            scope = hashlib.sha256(
                str(scope).strip().lower().encode()
            ).hexdigest()[:32]

        return f'throttle:{self.name}:{scope}'

    def consume(self, request, scope=None) -> bool:
        """
        Apunta un intento y dice si puede seguir.

        Se apunta **antes** de saber si acierta, para que acertar y fallar
        cuesten lo mismo: contando solo los fallos, enumerar sale gratis en
        cuanto se encuentra el primer valor valido.
        """
        key = self.key_for(request, scope)

        try:
            cache.add(key, 0, timeout=self.window)
            used = cache.incr(key)
        except ValueError:
            # La clave vencio entre el `add` y el `incr`. Es una carrera
            # normal, no una averia: cuenta como primer intento.
            used = 1
        except Exception:                                   # noqa: BLE001
            used = None

        if used is None:
            logger.error(
                'La cache no responde: no se puede aplicar el limite «%s», '
                'asi que la peticion de %s se rechaza en vez de dejarla pasar.',
                self.name, get_client_ip(request),
            )
            return False

        if used > self.limit:
            logger.warning(
                'Limite «%s» alcanzado desde %s (%s intentos en %ss).',
                self.name, get_client_ip(request), used, self.window,
            )
            return False

        return True

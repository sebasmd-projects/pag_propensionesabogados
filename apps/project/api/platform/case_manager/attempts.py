"""
Cuantas veces se puede fallar la clave del portal antes de que la IP descanse.

Por que hace falta
------------------
La clave del cliente es la inicial de su nombre mas los cuatro ultimos digitos
de su cedula: diez mil combinaciones como mucho, y muchas menos si se conoce el
nombre. Contra un formulario sin limite eso se agota en minutos. Cambiar la
clave por una propia esta fuera del alcance contratado, asi que mientras siga
siendo derivada, **el limite de intentos es lo unico que la sostiene**, y va
aqui y no como una mejora para despues.

Como cuenta
-----------
La cuenta es por IP y por ventana de tiempo, en la cache. No en la base: son
escrituras por cada intento fallido de cada visitante, y `ATOMIC_REQUESTS`
esta activo, asi que cada una se llevaria su transaccion. Lo que si se escribe
en la base es el bloqueo, que es un hecho que interesa conservar y consultar.

Al llegar al tope se crea un `IPBlockedModel`, que es el mismo mecanismo que
ya usa el proyecto y el que mira `DetectSuspiciousRequestMiddleware` en cada
peticion.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.common.utils.models import IPBlockedModel

logger = logging.getLogger(__name__)

#: Fallos permitidos por defecto dentro de la ventana antes de bloquear.
DEFAULT_MAX_ATTEMPTS = 8

#: Segundos que vive la cuenta por defecto. Fallar ocho veces en una hora es un
#: ataque; ocho veces en tres dias es alguien que no se acuerda de su clave.
DEFAULT_ATTEMPT_WINDOW = 60 * 60


def max_attempts() -> int:
    """
    El tope, leido **en cada llamada**.

    Es una funcion y no una constante de modulo a proposito: una constante se
    fija al importar, y entonces ni `override_settings` en una prueba ni un
    cambio de configuracion la mueven. Un limite de seguridad que no se puede
    bajar sin reiniciar es un limite que nadie baja.
    """
    return getattr(settings, 'CASE_MANAGER_MAX_ATTEMPTS', DEFAULT_MAX_ATTEMPTS)


def attempt_window() -> int:
    """Los segundos que vive la cuenta, leidos en cada llamada."""
    return getattr(
        settings, 'CASE_MANAGER_ATTEMPT_WINDOW', DEFAULT_ATTEMPT_WINDOW
    )


def client_ip(request) -> str:
    """
    De que IP viene la peticion.

    Detras de un proxy, `REMOTE_ADDR` es el proxy y todo el mundo comparte
    cuenta. Se mira `X-Forwarded-For` **solo** si el despliegue declara que
    hay un proxy de confianza delante (`USE_X_FORWARDED_FOR`); confiar en esa
    cabecera sin proxy es dejar que quien llama elija su propia identidad y se
    salte el contador cambiandola en cada intento.
    """
    if getattr(settings, 'USE_X_FORWARDED_FOR', False):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _key(ip: str) -> str:
    return f'case_manager:attempts:{ip}'


def attempts_for(ip: str) -> int:
    """Fallos acumulados por esa IP en la ventana actual."""
    return cache.get(_key(ip), 0)


def register_failure(ip: str) -> int:
    """
    Apunta un fallo y devuelve cuantos lleva. Bloquea al llegar al tope.

    La ventana **no** se renueva con cada fallo: se fija en el primero, para
    que insistir no pueda alargarla indefinidamente.
    """
    if not ip:
        return 0

    key = _key(ip)
    window = attempt_window()
    count = cache.get(key, 0) + 1
    if count == 1:
        cache.set(key, count, window)
    else:
        # `cache.incr` conserva el vencimiento que puso el primer fallo.
        try:
            count = cache.incr(key)
        except ValueError:  # vencio entre el `get` y el `incr`
            count = 1
            cache.set(key, count, window)

    if count >= max_attempts():
        block(ip, count)
        cache.delete(key)

    return count


def reset(ip: str) -> None:
    """Olvida los fallos. Se llama cuando alguien acierta."""
    if ip:
        cache.delete(_key(ip))


def block(ip: str, attempt_count: int) -> None:
    """
    Deja constancia del bloqueo para que lo vea el middleware.

    **`blocked_until` se rellena siempre.**
    `DetectSuspiciousRequestMiddleware` filtra por `blocked_until__gte=now`, y
    en SQL una fila con ese campo a NULL no cumple esa condicion: un bloqueo
    sin fecha es un bloqueo que no bloquea.
    """
    minutes = getattr(settings, 'IP_BLOCKED_TIME_IN_MINUTES', 30)
    IPBlockedModel.objects.create(
        current_ip=ip,
        reason=IPBlockedModel.ReasonsChoices.CASE_QUERY_ATTEMPTS,
        blocked_until=timezone.now() + timedelta(minutes=minutes),
        session_info={'attempt_count': attempt_count},
    )
    logger.warning(
        'IP %s bloqueada %s minutos tras %s intentos fallidos en el portal '
        'de consulta de procesos.',
        ip,
        minutes,
        attempt_count,
    )


def is_blocked(ip: str) -> bool:
    """Si esa IP tiene un bloqueo vigente."""
    if not ip:
        return False
    return IPBlockedModel.objects.filter(
        current_ip=ip,
        is_active=True,
        blocked_until__gte=timezone.now(),
    ).exists()

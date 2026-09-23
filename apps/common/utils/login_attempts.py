"""
Un solo contador de intentos fallidos de acceso, para las dos puertas.

El problema
-----------
Al acceso se entra por dos sitios: la contrasena y el codigo de seis cifras
que llega al correo. `django-axes` solo se entera del primero, porque cuenta
lo que pasa por `authenticate()`, y el codigo no pasa por ahi.

Dejarlo asi convierte el freno en un adorno: el tope de cinco intentos por
codigo se esquiva **pidiendo otro codigo**, y como esos fallos no se apuntan
en ningun sitio comun, quien prueba puede alternar entre las dos puertas sin
acercarse nunca al limite de ninguna.

La solucion
-----------
Que las dos puertas cuenten en el mismo sitio, y que ese sitio sea el que ya
existe. `note_failure()` dispara la senal `user_login_failed` que `axes`
escucha, asi que un codigo equivocado suma exactamente igual que una
contrasena equivocada; y `is_locked_out()` pregunta a `axes` si esta
conexion puede seguir intentandolo, para las dos.

Se pregunta **antes** de comprobar nada. Al reves se apuntarian los fallos sin
frenar nada.
"""

import logging

from django.contrib.auth.signals import user_login_failed

logger = logging.getLogger(__name__)


def _credentials(username: str) -> dict:
    """
    Las credenciales como las espera `axes`, normalizadas.

    Solo el nombre: la contrasena no tiene por que viajar hasta aqui, y una
    senal la reciben todos los receptores conectados, incluidos los que
    escriben en el registro.
    """
    return {'username': (username or '').strip().casefold()}


def note_failure(request, username: str, *, reason: str = '') -> None:
    """
    Apunta un intento fallido que no paso por `authenticate()`.

    Nunca lanza: esto se llama desde la validacion de un formulario, y un
    fallo del contador no puede impedir que la pantalla conteste.
    """
    try:
        user_login_failed.send(
            sender=__name__,
            credentials=_credentials(username),
            request=request,
        )
    except Exception:                                       # noqa: BLE001
        logger.exception(
            'No se pudo apuntar el intento fallido (%s).', reason or 'acceso'
        )


def is_locked_out(request, username: str = '') -> bool:
    """
    Si esta conexion ya gasto sus intentos.

    Se le pregunta a `axes` en vez de llevar la cuenta aparte: la cuenta
    aparte se desincroniza, y entonces una de las dos puertas frena y la otra
    no. Si `axes` no esta instalado o no responde, se deja pasar: este es un
    freno al tanteo, no la puerta; cerrarla por una averia del freno seria
    peor que el tanteo.
    """
    try:
        from axes.handlers.proxy import AxesProxyHandler
    except ImportError:
        return False

    try:
        return not AxesProxyHandler.is_allowed(request, _credentials(username))
    except Exception:                                       # noqa: BLE001
        logger.exception('No se pudo consultar el bloqueo de acceso.')
        return False

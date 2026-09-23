"""
El codigo de seis cifras que acredita al titular del proceso.

Por que se cambio la clave anterior
-----------------------------------
Lo que habia era una clave **derivada**: la inicial del nombre en mayuscula
mas los cuatro ultimos digitos de la cedula. Eso no acredita a nadie:

* son diez mil combinaciones como mucho, y muchas menos si se conoce el
  nombre;
* se calcula con la cedula delante, que es un dato que circula;
* y, sobre todo, **no prueba que quien la teclea sea el titular**. Un
  expediente lleva hechos, cuantias y el estado de un pleito; abrirselo a
  quien sepa una cedula y un apellido no es lo que exige el debido proceso.

Ahora el portal manda un codigo al correo que el despacho tiene registrado
como del cliente. Quien lo recibe demuestra que controla ese buzon, y ese
buzon es el que consta en el expediente.

Donde vive cada cosa, y por que
-------------------------------
**El codigo, en la sesion** --su HMAC, no el codigo-- porque es de esa
pantalla y de ese navegador: no tiene sentido que sobreviva a cerrar el
navegador, y guardarlo en la base seria dejar escrito un secreto de un solo
uso.

**La escalera de reenvios, en la base** (`ClientModel`), porque es lo
contrario: tiene que sobrevivir a tirar la galleta --si no, vaciar la sesion
reiniciaria la espera-- y tiene que ser la misma la vea el proceso que la
vea. Lo que frena el envio de correos al buzon de un tercero no puede
depender de con que trabajador de Passenger toque hablar.

La escalera
-----------
El primer envio es el que pide el cliente al consultar y no espera. A partir
de ahi::

    reenvio 2         1 minuto de espera
    reenvios 3, 4, 5  5 minutos cada uno
    despues del 5     una hora de bloqueo

y al terminar la hora el contador vuelve a cero, asi que el ciclo se repite:
un minuto, cinco, cinco, cinco y otra hora.

Por que escalonado y no un limite seco: quien acaba de pedir el codigo y no
lo ve suele volver a darle a los pocos segundos --el correo tarda--, y un
minuto basta para eso. Quien sigue dandole a los diez minutos ya no esta
esperando un correo; o el buzon registrado no es el suyo --y entonces lo que
necesita es llamar al despacho, que es lo que le dice la pantalla-- o no es
el titular.
"""

import hmac
import logging
import secrets
from datetime import timedelta
from hashlib import sha256

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import constant_time_compare

logger = logging.getLogger(__name__)

#: Donde vive el codigo dentro de la sesion.
SESSION_KEY = 'case_manager_otp'

#: Cuanto dura un codigo si no se configura otra cosa.
DEFAULT_TTL_MINUTES = 15

#: Cuantas veces se puede fallar **el mismo** codigo antes de invalidarlo.
#: Quien lo tiene delante puede equivocarse al teclear; nadie necesita cinco
#: intentos para copiar seis cifras de un correo.
MAX_ATTEMPTS = 5

#: La espera antes de cada envio, por orden. El primero no espera.
COOLDOWNS = (0, 60, 5 * 60, 5 * 60, 5 * 60)

#: Lo que se descansa al agotar la escalera, antes de volver a empezar.
CYCLE_BLOCK = 60 * 60


def ttl_minutes() -> int:
    """
    Cuanto dura un codigo, leido **en cada llamada**.

    Es una funcion y no una constante de modulo a proposito: una constante se
    fija al importar, y entonces ni `override_settings` en una prueba ni un
    cambio de configuracion la mueven.
    """
    return int(
        getattr(settings, 'CASE_MANAGER_OTP_TTL_MINUTES', DEFAULT_TTL_MINUTES)
    )


def generate_code() -> str:
    """Seis cifras, del generador criptografico y no de `random`."""
    return f'{secrets.randbelow(1_000_000):06d}'


def hash_code(code: str) -> str:
    """
    El codigo tal y como se guarda: HMAC-SHA256 con la clave del proyecto.

    Con HMAC y no con un `sha256` a secas porque un hash pelado de seis cifras
    se rompe con una tabla de un millon de entradas, que cabe en memoria. La
    clave es lo que hace que esa tabla no se pueda construir de antemano.
    """
    return hmac.new(
        settings.SECRET_KEY.encode(), code.encode(), sha256
    ).hexdigest()


# ---------------------------------------------------------------------------
# La escalera de reenvios
# ---------------------------------------------------------------------------

def _cycle_expired(client) -> bool:
    """Si el bloqueo de una hora ya paso y toca volver a empezar."""
    return bool(
        client.code_blocked_until
        and timezone.now() >= client.code_blocked_until
    )


def next_send_allowed_at(client):
    """
    Cuando se le puede mandar el siguiente codigo. `None` si ya mismo.

    Contesta con la **hora**, no con los segundos que faltan: los segundos
    caducan en cuanto se calculan, y quien recibe esto los pinta en una
    pantalla que el cliente puede tener abierta un rato.
    """
    if client.code_blocked_until and timezone.now() < client.code_blocked_until:
        return client.code_blocked_until

    if _cycle_expired(client) or not client.code_sends:
        return None

    if client.code_sends >= len(COOLDOWNS):
        # No deberia darse --al llegar al tope se pone `code_blocked_until`--
        # pero si una fila quedo a medias por un fallo a mitad de guardado, lo
        # seguro es esperar el bloqueo completo y no abrir la puerta.
        return (client.last_code_sent_at or timezone.now()) + timedelta(
            seconds=CYCLE_BLOCK
        )

    espera = COOLDOWNS[client.code_sends]

    if not espera or not client.last_code_sent_at:
        return None

    momento = client.last_code_sent_at + timedelta(seconds=espera)

    return momento if timezone.now() < momento else None


def can_send(client) -> bool:
    """Si ahora mismo se le puede mandar un codigo."""
    return next_send_allowed_at(client) is None


def register_send(client) -> None:
    """
    Apunta que acaba de salir un codigo, y bloquea si se agoto la escalera.

    Se guarda con `update_fields` para no reescribir la fila entera: esto
    corre en cada envio y lo unico que cambia son estos tres campos.
    """
    ahora = timezone.now()

    if _cycle_expired(client):
        client.code_sends = 0
        client.code_blocked_until = None

    client.code_sends += 1
    client.last_code_sent_at = ahora

    if client.code_sends >= len(COOLDOWNS):
        client.code_blocked_until = ahora + timedelta(seconds=CYCLE_BLOCK)
        logger.info(
            'Portal: el cliente %s agoto los %s codigos del ciclo; se bloquea '
            'una hora.',
            client.identification, len(COOLDOWNS),
        )

    client.save(update_fields=[
        'code_sends', 'last_code_sent_at', 'code_blocked_until', 'updated',
    ])


def reset_ladder(client) -> None:
    """
    Olvida la escalera. Se llama cuando el cliente **acierta** el codigo.

    Acertar demuestra que el correo registrado es suyo y que lo esta leyendo,
    que es justo lo que la escalera estaba comprobando. Dejarsela puesta
    castigaria la proxima consulta legitima por lo que hizo esta.
    """
    if not (client.code_sends or client.code_blocked_until):
        return

    client.code_sends = 0
    client.last_code_sent_at = None
    client.code_blocked_until = None
    client.save(update_fields=[
        'code_sends', 'last_code_sent_at', 'code_blocked_until', 'updated',
    ])


# ---------------------------------------------------------------------------
# El codigo
# ---------------------------------------------------------------------------

def issue(request, client) -> bool:
    """
    Emite un codigo, lo manda y lo deja anotado en la sesion.

    Devuelve si salio. `False` cuando el cliente no tiene correo registrado o
    cuando el correo no pudo salir: en los dos casos la pantalla tiene que
    decir otra cosa, porque prometer un codigo que no va a llegar deja a
    alguien esperando delante de un campo vacio.
    """
    if not client.email:
        logger.info(
            'Portal: el cliente %s no tiene correo registrado; no se le puede '
            'mandar un codigo.',
            client.identification,
        )
        return False

    code = generate_code()
    minutes = ttl_minutes()

    from .emails import send_access_code

    try:
        send_access_code(client=client, code=code, minutes=minutes)
    except Exception:                                       # noqa: BLE001
        logger.exception(
            'Portal: no se pudo mandar el codigo al cliente %s.',
            client.identification,
        )
        return False

    request.session[SESSION_KEY] = {
        'client_pk': str(client.pk),
        'code_hash': hash_code(code),
        'expires': (
            timezone.now() + timedelta(minutes=minutes)
        ).isoformat(),
        'attempts': 0,
    }
    request.session.modified = True

    register_send(client)

    return True


def pending_client_pk(request) -> str:
    """De quien es el codigo que espera esta sesion, si espera alguno."""
    return (request.session.get(SESSION_KEY) or {}).get('client_pk', '')


def verify(request, code: str) -> bool:
    """
    Comprueba el codigo de la sesion. Gasta un intento en cada llamada.

    Devuelve solo si acerto; quien es el cliente ya lo sabe la vista, que lo
    saco de `pending_client_pk()`. Al llegar al tope de intentos el codigo se
    tira: tantear cuesta pedir otro, y pedir otro tiene su escalera.
    """
    from datetime import datetime

    data = request.session.get(SESSION_KEY) or {}
    stored = data.get('code_hash')

    if not stored:
        return False

    expires = data.get('expires')

    if not expires or timezone.now() > datetime.fromisoformat(expires):
        clear(request)
        return False

    attempts = int(data.get('attempts', 0)) + 1
    data['attempts'] = attempts
    request.session[SESSION_KEY] = data
    request.session.modified = True

    if attempts > MAX_ATTEMPTS:
        logger.warning(
            'Portal: codigo invalidado tras %s intentos fallidos.', attempts
        )
        clear(request)
        return False

    if not constant_time_compare(stored, hash_code((code or '').strip())):
        return False

    # Un codigo que ya sirvio no puede volver a servir.
    clear(request)

    return True


def clear(request) -> None:
    """Borra el codigo de la sesion. Seguro de llamar de mas."""
    if request.session.pop(SESSION_KEY, None) is not None:
        request.session.modified = True

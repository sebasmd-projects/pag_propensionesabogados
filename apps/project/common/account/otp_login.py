"""
El codigo de seis cifras que llega al correo, y lo que lo sostiene.

Para que existe
---------------
Es la segunda puerta del acceso, y no es un segundo factor: es una
**alternativa a la contrasena**. Quien no se acuerda de la suya pide un
codigo, entra, y de paso deja de gastar los intentos que acabarian
bloqueandole la cuenta. Por eso se ofrece solo cuando hace falta --tras
varios fallos seguidos-- y no como primera opcion.

Que se guarda en la sesion, y que **no**
----------------------------------------
El codigo **no**. Lo que se guarda es su HMAC-SHA256 con la `SECRET_KEY` del
proyecto. La sesion va firmada, no cifrada: con el motor de base de datos el
contenido no sale del servidor, pero con `signed_cookies` --que es una linea
de configuracion de distancia-- el codigo viajaria en claro en la galleta.
Un hash no se puede volver a leer, y comparar hashes sirve igual.

La comparacion va con `constant_time_compare` porque comparar con `==` tarda
distinto segun cuantos caracteres coincidan, y eso, repetido, se mide.

Los tres frenos, y por que son tres
-----------------------------------
1. **Intentos por codigo** (`MAX_ATTEMPTS`): quien tiene el codigo delante
   puede equivocarse, pero no tantear un espacio de un millon.
2. **Envios por buzon** (`send_throttle`): el cupo es del **destinatario**,
   no de quien lo pide, para que rotar de IP no sirva de nada. Lo que se
   protege aqui no es el servidor: es que no se pueda llenar el buzon de un
   tercero a base de pedir codigos para su cuenta.
3. **Envios por conexion** (`send_ip_throttle`): el mismo freno visto del
   otro lado, para quien va probando cuentas distintas.

Lo que no se contesta nunca
---------------------------
Si la cuenta existe. Todas las respuestas de esta pantalla son iguales: se
pida un codigo para un correo real o inventado, se dice que se ha mandado. La
pantalla no puede ser un comprobador de cuentas, y por eso `has_live_code()`
mira si se **pidio** un codigo, no si se llego a emitir.
"""

import hmac
import logging
import secrets
from datetime import datetime, timedelta
from hashlib import sha256

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from apps.common.utils.throttling import RateLimit

logger = logging.getLogger(__name__)

#: Donde vive el codigo dentro de la sesion.
SESSION_KEY = 'login_otp'

#: Cuanto dura un codigo si no se configura otra cosa.
DEFAULT_TTL_MINUTES = 15

#: Cuantas veces se puede fallar **el mismo** codigo antes de invalidarlo.
MAX_ATTEMPTS = 5

#: Fallos de contrasena seguidos tras los que se ofrece el codigo. Tres, no
#: uno: ofrecerlo al primer fallo entrena a la gente a pedir un codigo en vez
#: de escribir su contrasena, y entonces el correo se vuelve el acceso normal.
FAILURES_BEFORE_OFFER = 3

#: Codigos por buzon. La llave es el correo, no la IP: ver el modulo.
send_throttle = RateLimit('login_otp_send', limit=3, window=10 * 60)

#: Codigos por conexion, para quien va probando cuentas distintas.
send_ip_throttle = RateLimit('login_otp_send_ip', limit=15, window=10 * 60)


def ttl_minutes() -> int:
    """
    Cuanto dura un codigo, leido **en cada llamada**.

    Es una funcion y no una constante de modulo a proposito: una constante se
    fija al importar, y entonces ni `override_settings` en una prueba ni un
    cambio de configuracion la mueven.
    """
    return int(getattr(settings, 'LOGIN_OTP_TTL_MINUTES', DEFAULT_TTL_MINUTES))


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


def backend_path() -> str:
    """
    Que backend anotar al entrar con codigo.

    Django lo exige cuando hay mas de uno configurado, y aqui hay dos --`axes`
    delante y el de siempre detras--. Se anota el de siempre: el de `axes` es
    un guardian que envuelve al otro, no una forma distinta de identificar a
    nadie, y anotarlo a el dejaria la sesion apuntando a un backend que en la
    siguiente peticion no sabria recargar al usuario.
    """
    for path in settings.AUTHENTICATION_BACKENDS:
        if 'axes' not in path.lower():
            return path

    return settings.AUTHENTICATION_BACKENDS[0]


def find_user(identifier: str):
    """
    La cuenta a la que mandarle el codigo, o `None`.

    Se busca por nombre de usuario **o** por correo porque la pantalla admite
    los dos, y quien no se acuerda de su contrasena tampoco tiene por que
    acordarse de cual de los dos puso.

    Solo cuentas activas: a una desactivada no se le manda un codigo que no le
    va a servir para entrar.
    """
    identifier = (identifier or '').strip()

    if not identifier:
        return None

    return get_user_model()._default_manager.filter(
        Q(username__iexact=identifier) | Q(email__iexact=identifier),
        is_active=True,
    ).first()


def issue(request, identifier: str) -> bool:
    """
    Emite un codigo y lo manda. Devuelve si **se acepto la peticion**.

    Devolver `True` no quiere decir que exista la cuenta ni que saliera el
    correo: quiere decir que la peticion no choco con ningun freno. La
    diferencia importa porque lo que se le ensena a quien pregunta sale de
    este valor, y distinguir «mandado» de «esa cuenta no existe» convertiria
    la pantalla en un comprobador de cuentas.

    `False` es siempre lo mismo: has pedido demasiados.
    """
    identifier = (identifier or '').strip().lower()

    if not send_ip_throttle.consume(request):
        return False

    user = find_user(identifier)

    # La marca se pone **aunque no haya cuenta**: es lo que hace que la
    # pantalla siguiente diga «te hemos mandado un codigo» en los dos casos.
    request.session[SESSION_KEY] = {
        'requested': timezone.now().isoformat(),
        'identifier': identifier,
        'attempts': 0,
    }
    request.session.modified = True

    if user is None or not user.email:
        logger.info(
            'Codigo de acceso pedido para un identificador sin cuenta o sin '
            'correo; no se manda nada y se contesta igual.'
        )
        return True

    # El cupo del buzon se consulta con el **correo de la cuenta**, no con lo
    # que se escribio: si no, pedir el codigo una vez por el usuario y otra
    # por el correo abriria dos cupos para el mismo buzon.
    if not send_throttle.consume(request, scope=user.email):
        request.session.pop(SESSION_KEY, None)
        return False

    code = generate_code()
    minutes = ttl_minutes()

    request.session[SESSION_KEY] = {
        'requested': timezone.now().isoformat(),
        'identifier': identifier,
        'attempts': 0,
        'code_hash': hash_code(code),
        'user_pk': str(user.pk),
        'expires': (
            timezone.now() + timedelta(minutes=minutes)
        ).isoformat(),
    }
    request.session.modified = True

    from .emails import send_login_otp_email

    try:
        send_login_otp_email(user=user, code=code, minutes=minutes)
    except Exception:                                       # noqa: BLE001
        # Si el correo no sale, el codigo emitido no le sirve a nadie: se
        # borra, para que la pantalla no prometa uno que no va a llegar y
        # para no dejar un hash vivo sin dueno.
        logger.exception(
            'No se pudo mandar el codigo de acceso; se descarta el emitido.'
        )
        request.session.pop(SESSION_KEY, None)
        return False

    return True


def contact_email() -> str:
    """A quien escribir si llega un codigo que no se pidio."""
    from .emails import CONTACT_EMAIL

    return CONTACT_EMAIL


def remember_identifier(request, identifier: str) -> None:
    """
    Se queda con lo que se tecleo, sin emitir codigo.

    Hace falta para el boton «entrar con un codigo», que abre la pantalla
    antes de saber a quien mandarselo: asi el identificador vuelve escrito y
    no hay que teclearlo dos veces.
    """
    data = dict(request.session.get(SESSION_KEY) or {})
    data['identifier'] = (identifier or '').strip().lower()
    request.session[SESSION_KEY] = data
    request.session.modified = True


def entered_identifier(request) -> str:
    """Lo ultimo que se tecleo en la pantalla del codigo."""
    return (request.session.get(SESSION_KEY) or {}).get('identifier', '')


def has_live_code(request) -> bool:
    """
    Si en esta sesion se **pidio** un codigo hace poco.

    Mira `requested`, no `code_hash`, y eso es deliberado: si mirara el hash,
    la pantalla diria «te hemos mandado un codigo» solo cuando la cuenta
    existe, y quien prueba correos sabria cuales estan dados de alta con solo
    leer el aviso.
    """
    data = request.session.get(SESSION_KEY) or {}
    return bool(data.get('requested'))


def verify(request, code: str):
    """
    Comprueba el codigo. Devuelve la cuenta, o `None`.

    Gasta un intento en cada llamada y tira el codigo al llegar al tope, para
    que tantear cueste pedir otro --y pedir otro tiene su propio freno--.
    """
    data = request.session.get(SESSION_KEY) or {}
    stored = data.get('code_hash')

    if not stored:
        return None

    expires = data.get('expires')

    if not expires or timezone.now() > datetime.fromisoformat(expires):
        clear(request)
        return None

    attempts = int(data.get('attempts', 0)) + 1
    data['attempts'] = attempts
    request.session[SESSION_KEY] = data
    request.session.modified = True

    if attempts > MAX_ATTEMPTS:
        logger.warning(
            'Codigo de acceso invalidado tras %s intentos fallidos.', attempts
        )
        clear(request)
        return None

    if not constant_time_compare(stored, hash_code((code or '').strip())):
        return None

    user = get_user_model()._default_manager.filter(
        pk=data.get('user_pk'), is_active=True
    ).first()

    if user is not None:
        # Django exige saber por que backend entro cada sesion cuando hay mas
        # de uno configurado, y aqui no ha pasado por `authenticate()`. Sin
        # esto, `login()` busca `user.backend`, no lo encuentra y termina en
        # «You have multiple authentication backends configured»: un 500 en la
        # pantalla de acceso justo despues de acertar el codigo.
        user.backend = backend_path()

    # El codigo se quema acierte o no en el ultimo paso: uno que ya sirvio no
    # puede volver a servir, y uno cuya cuenta se desactivo entre medias
    # tampoco.
    clear(request)

    return user


def clear(request) -> None:
    """Borra el codigo de la sesion. Seguro de llamar de mas."""
    if request.session.pop(SESSION_KEY, None) is not None:
        request.session.modified = True

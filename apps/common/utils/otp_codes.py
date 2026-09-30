"""Códigos de un solo uso compartidos por los portales."""

import hmac
import secrets
from hashlib import sha256

from django.conf import settings


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


def codes_match(code: str, code_hash: str) -> bool:
    """Compara el HMAC del código en tiempo constante."""
    return hmac.compare_digest(hash_code(code), code_hash)

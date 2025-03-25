# apps/common/utils/token_utils.py
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings

SECRET_KEY = settings.SECRET_KEY

signer = TimestampSigner(SECRET_KEY)


def generate_token(user_id: str) -> str:
    return signer.sign(user_id).decode()


def verify_token(token: str, max_age=3600) -> str:
    try:
        return signer.unsign(token, max_age=max_age).decode()
    except SignatureExpired:
        raise ValueError("Token expirado")
    except BadSignature:
        raise ValueError("Token inválido")

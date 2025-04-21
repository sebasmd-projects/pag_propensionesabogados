# apps/common/utils/token_utils.py
import datetime
import time

from django.conf import settings
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SECRET_KEY = settings.SECRET_KEY
TOKEN_TIMEOUT = settings.ATTLAS_TOKEN_TIMEOUT

serializer = URLSafeTimedSerializer(SECRET_KEY)


def generate_token(user_id: str) -> str:
    return serializer.dumps({"user_id": user_id})


def verify_token(token: str, max_age=TOKEN_TIMEOUT) -> str:
    try:
        data, timestamp = serializer.loads(
            token, max_age=max_age, return_timestamp=True
        )
        user_id = data["user_id"]
        return user_id
    except SignatureExpired:
        raise ValueError("Token expirado")
    except BadSignature:
        raise ValueError("Token inválido")

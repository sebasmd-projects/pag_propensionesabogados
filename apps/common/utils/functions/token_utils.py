from django.conf import settings
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SECRET_KEY = settings.SECRET_KEY
TOKEN_TIMEOUT = settings.ATTLAS_TOKEN_TIMEOUT
serializer = URLSafeTimedSerializer(SECRET_KEY)


def generate_token(user_id: str, scope="platform") -> str:
    return serializer.dumps({"user_id": user_id, "scope": scope})


def verify_token(token: str, max_age=TOKEN_TIMEOUT, scopes=("platform",)) -> str:
    try:
        # Authenticate the payload before choosing its scope-specific lifetime.
        data = serializer.loads(token)
        if not isinstance(data, dict) or data.get("scope", "platform") not in scopes:
            raise ValueError("Token inválido")
        if data.get("scope", "platform") == "lookup":
            max_age = settings.ATTLAS_LOOKUP_TOKEN_TIMEOUT
        data = serializer.loads(token, max_age=max_age)
        return data["user_id"]
    except SignatureExpired:
        raise ValueError("Token expirado")
    except (BadSignature, KeyError, TypeError):
        raise ValueError("Token inválido")

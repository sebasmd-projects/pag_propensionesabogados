from rest_framework.exceptions import AuthenticationFailed

from apps.common.utils.functions import verify_token
from .models import AttlasInsolvencyAuthModel


class BearerTokenAuthentication:
    allowed_scopes = ("platform",)

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        try:
            user_id = verify_token(token, scopes=self.allowed_scopes)
            user = AttlasInsolvencyAuthModel.objects.get(id=user_id)
            return (user, None)
        except Exception as e:
            raise AuthenticationFailed(str(e))

    def authenticate_header(self, request):
        return 'Bearer'


class LookupOrPlatformTokenAuthentication(BearerTokenAuthentication):
    allowed_scopes = ("platform", "lookup")

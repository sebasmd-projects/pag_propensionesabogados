from rest_framework.exceptions import AuthenticationFailed

from apps.common.utils.functions import verify_token
from .models import AttlasInsolvencyAuthModel


class BearerTokenAuthentication:
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        try:
            user_id = verify_token(token)
            user = AttlasInsolvencyAuthModel.objects.get(id=user_id)
            return (user, None)
        except Exception as e:
            raise AuthenticationFailed(str(e))

    def authenticate_header(self, request):
        return 'Bearer'



#  apps/project/api/platform/insolvency_form/api/views.py

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated

from apps.common.utils.functions import verify_token
from apps.project.api.platform.auth_platform.api.views import \
    AttlasInsolvencyAuthModel

from ..models import AttlasInsolvencyFormModel
from .serializers import AttlasInsolvencyFormSerializer


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


class AttlasInsolvencyFormAPIView(CreateAPIView):
    serializer_class = AttlasInsolvencyFormSerializer
    queryset = AttlasInsolvencyFormModel.objects.all()
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

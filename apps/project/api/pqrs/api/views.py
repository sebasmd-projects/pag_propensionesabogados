from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView

from ..models import PQRSModel
from .serializers import PQRSModelSerializer

from drf_spectacular.utils import extend_schema


@extend_schema(tags=['PQRS Attlas'])
class PQRSModelCreateAPIView(CreateAPIView):
    # La recepción de PQRS está disponible para cualquier visitante.
    permission_classes = [AllowAny]

    serializer_class = PQRSModelSerializer
    queryset = PQRSModel.objects.all()

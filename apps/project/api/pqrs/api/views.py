from rest_framework.generics import CreateAPIView

from ..models import PQRSModel
from .serializers import PQRSModelSerializer

from drf_spectacular.utils import extend_schema


@extend_schema(tags=['PQRS Attlas'])
class PQRSModelCreateAPIView(CreateAPIView):
    serializer_class = PQRSModelSerializer
    queryset = PQRSModel.objects.all()

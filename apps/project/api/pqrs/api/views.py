from rest_framework.generics import CreateAPIView

from ..models import PQRSModel
from .serializers import PQRSModelSerializer


class PQRSModelCreateAPIView(CreateAPIView):
    serializer_class = PQRSModelSerializer
    queryset = PQRSModel.objects.all()

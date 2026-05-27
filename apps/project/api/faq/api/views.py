from rest_framework.generics import ListAPIView

from ..models import MainFAQModel, OtherFAQModel
from .serializers import MainFAQModelSerializer, OtherFAQModelSerializer

from drf_spectacular.utils import extend_schema


@extend_schema(tags=['FAQ'])
class MainFAQListAPIView(ListAPIView):
    serializer_class = MainFAQModelSerializer
    queryset = MainFAQModel.objects.all()


@extend_schema(tags=['FAQ'])
class OtherFAQListAPIView(ListAPIView):
    serializer_class = OtherFAQModelSerializer
    queryset = OtherFAQModel.objects.all()

from rest_framework.generics import ListAPIView

from ..models import MainFAQModel, OtherFAQModel
from .serializers import MainFAQModelSerializer, OtherFAQModelSerializer


class MainFAQListAPIView(ListAPIView):
    serializer_class = MainFAQModelSerializer
    queryset = MainFAQModel.objects.all()


class OtherFAQListAPIView(ListAPIView):
    serializer_class = OtherFAQModelSerializer
    queryset = OtherFAQModel.objects.all()

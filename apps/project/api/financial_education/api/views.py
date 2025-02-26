from rest_framework.generics import ListAPIView

from ..models import FinancialEducationModel
from .serializers import FinancialEducationModelSerializer


class FinancialEducationListAPIView(ListAPIView):
    serializer_class = FinancialEducationModelSerializer
    queryset = FinancialEducationModel.objects.all()

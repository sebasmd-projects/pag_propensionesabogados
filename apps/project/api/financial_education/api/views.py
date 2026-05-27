from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema

from ..models import FinancialEducationModel
from .serializers import FinancialEducationModelSerializer

@extend_schema(tags=['Educación Financiera'])
class FinancialEducationListAPIView(ListAPIView):
    serializer_class = FinancialEducationModelSerializer
    queryset = FinancialEducationModel.objects.all()

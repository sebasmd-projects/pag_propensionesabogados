from rest_framework.permissions import AllowAny
from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema

from ..models import FinancialEducationModel
from .serializers import FinancialEducationModelSerializer

@extend_schema(tags=['Educación Financiera'])
class FinancialEducationListAPIView(ListAPIView):
    # La educación financiera es contenido público del sitio.
    permission_classes = [AllowAny]

    serializer_class = FinancialEducationModelSerializer
    queryset = FinancialEducationModel.objects.all()

from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView

from .serializers import ConctactModelSerializer
from ..models import ContactModel


class ContactCreateAPIView(CreateAPIView):
    # El formulario de contacto recibe consultas de visitantes sin cuenta.
    permission_classes = [AllowAny]

    serializer_class = ConctactModelSerializer
    queryset = ContactModel.objects.all()

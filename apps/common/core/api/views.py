from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..throttling import TOO_MANY_REQUESTS_DETAIL, contact_by_ip
from .serializers import ConctactModelSerializer
from ..models import ContactModel


class ContactCreateAPIView(CreateAPIView):
    # El formulario de contacto recibe consultas de visitantes sin cuenta.
    permission_classes = [AllowAny]

    serializer_class = ConctactModelSerializer
    queryset = ContactModel.objects.all()

    def create(self, request, *args, **kwargs):
        # El mismo cubo que la portada (`core:index`): son dos puertas al
        # mismo formulario. Se apunta antes de validar el cuerpo, y falla
        # cerrado si la cache no responde (ver `core/throttling.py`).
        if not contact_by_ip.consume(request):
            return Response(TOO_MANY_REQUESTS_DETAIL, status=429)

        return super().create(request, *args, **kwargs)

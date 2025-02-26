from rest_framework.generics import CreateAPIView

from .serializers import ConctactModelSerializer
from ..models import ContactModel


class ContactCreateAPIView(CreateAPIView):
    serializer_class = ConctactModelSerializer
    queryset = ContactModel.objects.all()

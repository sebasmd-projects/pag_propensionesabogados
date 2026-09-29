# apps/project/api/platform/calculator/views.py
from rest_framework import viewsets, mixins, status
from apps.common.utils.api_keys import HasServerKey
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from apps.project.api.platform.insolvency_form.models import AttlasInsolvencyFormModel
from .serializers import (
    ClientDataSerializer,
    ClientCreateSerializer,
    ClientUpdateSerializer,
)


@extend_schema(tags=['Clients'])
class ClientViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    """
    ViewSet unificado para clientes:
    - create (POST) -> /clients/
    - retrieve (GET), update (PUT), partial_update (PATCH) -> /clients/{id}/
    """
    queryset = AttlasInsolvencyFormModel.objects.all()
    permission_classes = [HasServerKey]

    def get_serializer_class(self):
        if self.action == 'create':
            return ClientCreateSerializer
        if self.action in ('update', 'partial_update'):
            return ClientUpdateSerializer
        # retrieve y cualquier otro devuelven los datos completos
        return ClientDataSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = serializer.save()  # Retorna el AttlasInsolvencyFormModel creado
        output_serializer = ClientDataSerializer(form)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        output_serializer = ClientDataSerializer(updated_instance)
        return Response(output_serializer.data)
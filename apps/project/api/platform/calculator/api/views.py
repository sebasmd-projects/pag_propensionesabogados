# apps/project/api/platform/calculator/views.py
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView

from apps.common.utils.models import hash_value
from apps.project.api.platform.auth_platform.models import AttlasInsolvencyAuthModel
from apps.project.api.platform.insolvency_form.models import AttlasInsolvencyFormModel
from ..models import InterestRateModel
from .serializers import (
    ClientSearchSerializer,
    ClientDataSerializer,
    ClientCreateSerializer,
    ClientUpdateSerializer,
    InterestRateSerializer,
)


class ClientViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    """
    ViewSet unificado para clientes:
    - search (GET)  -> /clients/search/
    - create (POST) -> /clients/
    - retrieve (GET), update (PUT), partial_update (PATCH) -> /clients/{id}/
    """
    queryset = AttlasInsolvencyFormModel.objects.all()
    permission_classes = [AllowAny]  # Ajustar según necesidades de seguridad

    def get_serializer_class(self):
        if self.action == 'create':
            return ClientCreateSerializer
        if self.action == 'search':
            return ClientSearchSerializer
        if self.action in ('update', 'partial_update'):
            return ClientUpdateSerializer
        # retrieve y cualquier otro devuelven los datos completos
        return ClientDataSerializer

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        # Validar parámetros de consulta con el serializador
        search_serializer = self.get_serializer(data=request.query_params)
        search_serializer.is_valid(raise_exception=True)
        cedula = search_serializer.validated_data['cedula']
        birth_date = search_serializer.validated_data['birthDate']

        doc_hash = hash_value(cedula)
        birth_hash = hash_value(str(birth_date))

        try:
            auth_user = AttlasInsolvencyAuthModel.objects.get(
                document_number_hash=doc_hash,
                birth_date_hash=birth_hash
            )
        except AttlasInsolvencyAuthModel.DoesNotExist:
            return Response(
                {'detail': 'Usuario no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        form = AttlasInsolvencyFormModel.objects.filter(user=auth_user).first()
        if not form:
            # Si no existe formulario, devolvemos datos básicos del registro de autenticación
            return Response({
                'id': auth_user.id,
                'document_number': auth_user.document_number,
                'birth_date': auth_user.birth_date,
                'first_name': '',
                'last_name': '',
                'email': '',
                'phone': '',
                'address': ''
            })

        output_serializer = ClientDataSerializer(form)
        return Response(output_serializer.data)

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


class InterestRateView(ListCreateAPIView):
    """
    Endpoint que maneja la tasa de usura. Solo existe un único registro (el último).
    - GET: retorna la tasa más reciente (única).
    - POST: sobre-escribe la tasa existente creando un nuevo registro.
    """
    serializer_class = InterestRateSerializer

    def get_queryset(self):
        return InterestRateModel.objects.all().order_by('-effective_date')[:1]

    def perform_create(self, serializer):
        InterestRateModel.objects.all().delete()
        serializer.save()
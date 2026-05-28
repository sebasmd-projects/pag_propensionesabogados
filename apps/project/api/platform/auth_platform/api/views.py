# apps/project/api/platform/auth_platform/api/views.py

from django.conf import settings
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.common.utils.functions import generate_token, verify_token
from apps.common.utils.models import hash_value

from ..models import AttlasInsolvencyAuthModel
from .serializers import (
    AttlasInsolvencyAuthConsultantsRegisterSerializer,
    AttlasInsolvencyAuthRegisterSerializer,
    AttlasInsolvencyAuthSerializer,
    ClientSearchSerializer,
    ClientResponseSerializer
)


@extend_schema(tags=['Clients'])
class ClientSearchView(APIView):
    """
    GET /api/v1/clients/search/?documentNumber=xxx&birthDate=yyyy-mm-dd

    Busca por los campos _hash para no comparar texto cifrado.
    Devuelve datos en claro + form_id del formulario de insolvencia.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        params = ClientSearchSerializer(data=request.query_params)
        if not params.is_valid():
            return Response(params.errors, status=status.HTTP_400_BAD_REQUEST)

        dn_hash = hash_value(params.validated_data['documentNumber'])
        bd_hash = hash_value(
            params.validated_data['birthDate'].strftime('%Y-%m-%d')
        )

        try:
            user = AttlasInsolvencyAuthModel.objects.select_related(
                'insolvency_form'
            ).get(
                document_number_hash=dn_hash,
                birth_date_hash=bd_hash,
            )
        except AttlasInsolvencyAuthModel.DoesNotExist:
            return Response(
                {'detail': 'No encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(ClientResponseSerializer().to_representation(user))


@extend_schema(tags=['Auth Attlas'])
class AttlasInsolvencyAuthRegisterAPIView(CreateAPIView):
    serializer_class = AttlasInsolvencyAuthRegisterSerializer
    queryset = AttlasInsolvencyAuthModel.objects.all()


@extend_schema(tags=['Auth Attlas'])
class AttlasInsolvencyAuthConsultantsRegisterAPIView(CreateAPIView):
    serializer_class = AttlasInsolvencyAuthConsultantsRegisterSerializer
    queryset = AttlasInsolvencyAuthModel.objects.all()


@extend_schema(tags=['Auth Attlas'])
class AttlasInsolvencyAuthLoginAPIView(APIView):
    def post(self, request):

        serializer = AttlasInsolvencyAuthSerializer(data=request.data)

        if serializer.is_valid():

            token = generate_token(str(serializer.validated_data['user_id']))

            return Response(
                {
                    'token': token,
                    'expires_in': settings.ATTLAS_TOKEN_TIMEOUT,
                    # AttlasInsolvencyAuthConsultantsModel.user
                    'user': request.data['user'],
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Auth Attlas'])
class TokenInfoAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            return Response({'detail': 'Token no proporcionado'}, status=400)

        try:
            user_id = verify_token(token)
            user = AttlasInsolvencyAuthModel.objects.get(id=user_id)

            return Response({
                'document_number': user.document_number,
                'birth_date': user.birth_date,
            })
        except Exception as e:
            return Response({'detail': str(e)}, status=401)

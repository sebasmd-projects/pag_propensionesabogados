# apps/project/api/platform/auth_platform/api/views.py

from django.conf import settings
from rest_framework import status
from rest_framework.generics import CreateAPIView
from apps.common.utils.api_keys import HasServerKey
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.common.utils.functions import generate_token, verify_token
from apps.common.utils.throttling import RateLimit
from apps.common.utils.login_attempts import is_locked_out

from ..models import AttlasInsolvencyAuthModel
from .serializers import (
    AttlasInsolvencyAuthConsultantsRegisterSerializer,
    AttlasInsolvencyAuthRegisterSerializer,
    AttlasInsolvencyAuthSerializer,
    ClientSearchSerializer,
)


attlas_login_ip = RateLimit('attlas_login_ip', limit=10, window=15 * 60)

clients_search_ip = RateLimit('clients_search_ip', limit=20, window=10*60)
clients_search_doc = RateLimit('clients_search_doc', limit=5, window=10*60)


@extend_schema(tags=['Clients'])
class ClientSearchView(APIView):
    """
    GET /api/v1/clients/search/?documentNumber=xxx&birthDate=yyyy-mm-dd

    Búsqueda deshabilitada hasta el flujo OTP: valida y limita solicitudes,
    y responde 404 uniforme sin consultar ni revelar datos de clientes.
    """
    permission_classes = [HasServerKey]

    def get(self, request):
        params = ClientSearchSerializer(data=request.query_params)
        if not params.is_valid():
            return Response(params.errors, status=status.HTTP_400_BAD_REQUEST)

        document_number = params.validated_data['documentNumber'].strip().lower()
        ip_allowed = clients_search_ip.consume(request)
        doc_allowed = clients_search_doc.consume(request, scope=document_number)
        if not ip_allowed or not doc_allowed:
            return Response(
                {'detail': 'Demasiadas solicitudes. Intente más tarde.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Deshabilitado de facto hasta OTP: cédula + fecha no son credenciales.
        # El 404 uniforme evita un oráculo que revele quién es cliente.
        return Response(
            {'detail': 'No encontrado'},
            status=status.HTTP_404_NOT_FOUND,
        )


@extend_schema(tags=['Auth Attlas'])
class AttlasInsolvencyAuthRegisterAPIView(CreateAPIView):
    permission_classes = [HasServerKey]

    serializer_class = AttlasInsolvencyAuthRegisterSerializer
    queryset = AttlasInsolvencyAuthModel.objects.all()


@extend_schema(tags=['Auth Attlas'])
class AttlasInsolvencyAuthConsultantsRegisterAPIView(CreateAPIView):
    permission_classes = [HasServerKey]

    serializer_class = AttlasInsolvencyAuthConsultantsRegisterSerializer
    queryset = AttlasInsolvencyAuthModel.objects.all()


@extend_schema(tags=['Auth Attlas'])
class AttlasInsolvencyAuthLoginAPIView(APIView):
    permission_classes = [HasServerKey]

    def post(self, request):

        username = request.data.get('user', '')
        username = username.strip().upper() if isinstance(username, str) else ''
        if not attlas_login_ip.consume(request) or is_locked_out(
            request, username=username,
        ):
            return Response(
                {'detail': 'Demasiados intentos. Intente más tarde.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = AttlasInsolvencyAuthSerializer(
            data=request.data, context={'request': request},
        )

        if serializer.is_valid():

            token = generate_token(str(serializer.validated_data['user_id']))

            return Response(
                {
                    'token': token,
                    'expires_in': settings.ATTLAS_TOKEN_TIMEOUT,
                    # AttlasInsolvencyAuthConsultantsModel.user
                    'user': serializer.validated_data['user'],
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Auth Attlas'])
class TokenInfoAPIView(APIView):
    permission_classes = [HasServerKey]

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
        except (ValueError, AttlasInsolvencyAuthModel.DoesNotExist):
            return Response({'detail': 'Token inválido o expirado.'}, status=401)

# apps/project/api/platform/auth_platform/api/views.py

import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils.api_keys import HasServerKey
from apps.common.utils.functions import generate_token, verify_token
from apps.common.utils.login_attempts import is_locked_out
from apps.common.utils.models import hash_value
from apps.common.utils.otp_codes import codes_match, generate_code, hash_code
from apps.common.utils.throttling import RateLimit

from ..emails import send_lookup_code
from ..models import AttlasInsolvencyAuthModel, ClientLookupChallenge
from .serializers import (
    AttlasInsolvencyAuthConsultantsRegisterSerializer,
    AttlasInsolvencyAuthRegisterSerializer,
    AttlasInsolvencyAuthSerializer,
    ClientLookupVerifySerializer,
    ClientResponseSerializer,
    ClientSearchSerializer,
)


attlas_login_ip = RateLimit('attlas_login_ip', limit=10, window=15 * 60)

logger = logging.getLogger(__name__)


def _send_lookup_code(email, code):
    try:
        send_lookup_code(email, code)
    except Exception:
        logger.exception('Fallo al enviar el código de verificación de calculadora.')
    finally:
        close_old_connections()


def _start_lookup_email(email, code):
    try:
        threading.Thread(target=_send_lookup_code, args=(email, code), daemon=True).start()
    except Exception:
        logger.exception('No se pudo iniciar el envío del código de calculadora.')


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


# Separate buckets prevent the public calculator from spending login quotas.
clients_lookup_ip = RateLimit('clients_lookup_ip', limit=10, window=10 * 60)
clients_lookup_doc = RateLimit('clients_lookup_doc', limit=3, window=60 * 60)
clients_lookup_verify_ip = RateLimit('clients_lookup_verify_ip', limit=30, window=10 * 60)
LOOKUP_LIMIT_DETAIL = {'detail': 'Demasiadas solicitudes. Intente más tarde.'}
LOOKUP_INVALID_DETAIL = {'detail': 'Código inválido o caducado.'}


@extend_schema(tags=['Clients'])
class ClientLookupView(APIView):
    permission_classes = [HasServerKey]

    def post(self, request):
        params = ClientSearchSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        document = params.validated_data['documentNumber']
        ip_allowed = clients_lookup_ip.consume(request)
        doc_allowed = clients_lookup_doc.consume(request, scope=document.strip().lower())
        if not ip_allowed or not doc_allowed:
            return Response(LOOKUP_LIMIT_DETAIL, status=429)

        user = AttlasInsolvencyAuthModel.objects.select_related('insolvency_form').filter(
            document_number_hash=hash_value(document),
            birth_date_hash=hash_value(params.validated_data['birthDate'].strftime('%Y-%m-%d')),
        ).first()
        form = getattr(user, 'insolvency_form', None)
        email = (form.debtor_email or '').strip() if form else ''
        code = generate_code()
        with transaction.atomic():
            challenge = ClientLookupChallenge.objects.create(
                auth_user=user if email else None,
                code_hash=hash_code(code),
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            if email:
                # El correo no necesita contexto HTTP; el envío no bloquea la respuesta.
                transaction.on_commit(lambda: _start_lookup_email(email, code))
        return Response({'challenge_id': str(challenge.id)}, status=202)


@extend_schema(tags=['Clients'])
class ClientLookupVerifyView(APIView):
    permission_classes = [HasServerKey]

    def post(self, request):
        if not clients_lookup_verify_ip.consume(request):
            return Response(LOOKUP_LIMIT_DETAIL, status=429)
        params = ClientLookupVerifySerializer(data=request.data)
        if not params.is_valid():
            return Response(LOOKUP_INVALID_DETAIL, status=400)
        with transaction.atomic():
            challenge = ClientLookupChallenge.objects.select_for_update().filter(
                pk=params.validated_data['challenge_id'],
            ).first()
            now = timezone.now()
            if (challenge is None or challenge.expires_at <= now
                    or challenge.used_at is not None or challenge.attempts >= 5):
                return Response(LOOKUP_INVALID_DETAIL, status=400)
            challenge.attempts += 1
            challenge.save(update_fields=['attempts', 'updated'])
            if (not codes_match(params.validated_data['code'], challenge.code_hash)
                    or challenge.auth_user_id is None):
                return Response(LOOKUP_INVALID_DETAIL, status=400)
            challenge.used_at = now
            challenge.save(update_fields=['used_at', 'updated'])
            user = challenge.auth_user
            data = ClientResponseSerializer(user).data
            data['token'] = generate_token(str(user.id), scope='lookup')
            data['expires_in'] = settings.ATTLAS_LOOKUP_TOKEN_TIMEOUT
        return Response(data)

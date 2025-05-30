# apps/project/api/platform/auth_platform/api/views.py

from django.conf import settings
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils.functions import generate_token, verify_token

from ..models import AttlasInsolvencyAuthModel
from .serializers import (AttlasInsolvencyAuthConsultantsRegisterSerializer,
                          AttlasInsolvencyAuthRegisterSerializer,
                          AttlasInsolvencyAuthSerializer)


class AttlasInsolvencyAuthRegisterAPIView(CreateAPIView):
    serializer_class = AttlasInsolvencyAuthRegisterSerializer
    queryset = AttlasInsolvencyAuthModel.objects.all()


class AttlasInsolvencyAuthConsultantsRegisterAPIView(CreateAPIView):
    serializer_class = AttlasInsolvencyAuthConsultantsRegisterSerializer
    queryset = AttlasInsolvencyAuthModel.objects.all()


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

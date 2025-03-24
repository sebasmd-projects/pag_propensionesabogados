from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import AttlasInsolvencyAuthModel
from .serializers import (AttlasInsolvencyAuthRegisterSerializer,
                          AttlasInsolvencyAuthSerializer)


class AttlasInsolvencyAuthLoginAPIView(APIView):
    def post(self, request):
        serializer = AttlasInsolvencyAuthSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AttlasInsolvencyAuthRegisterAPIView(CreateAPIView):
    serializer_class = AttlasInsolvencyAuthRegisterSerializer
    queryset = AttlasInsolvencyAuthModel.objects.all()

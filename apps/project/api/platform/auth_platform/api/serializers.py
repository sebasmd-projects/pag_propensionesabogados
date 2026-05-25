# apps/project/api/platform/auth_platform/api/serializers.py

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import (AttlasInsolvencyAuthConsultantsModel,
                      AttlasInsolvencyAuthModel, hash_value)


class AttlasInsolvencyAuthSerializer(serializers.Serializer):
    document_number = serializers.CharField()
    birth_date = serializers.DateField()
    password = serializers.CharField()
    user = serializers.CharField()  # Iniciales del asesor

    def validate(self, data):
        doc_hash = hash_value(data['document_number'])
        birth_hash = hash_value(str(data['birth_date']))
        password = data['password']
        user = data['user'].upper()

        # 1. Verificar existencia del usuario (cliente)
        try:
            auth_user = AttlasInsolvencyAuthModel.objects.get(
                document_number_hash=doc_hash,
                birth_date_hash=birth_hash
            )
        except AttlasInsolvencyAuthModel.DoesNotExist:
            raise serializers.ValidationError({
                'document_number': _('Cédula no encontrada con esa fecha de nacimiento.')
            })

        # 2. Verificar existencia del asesor con las iniciales
        try:
            consultant = AttlasInsolvencyAuthConsultantsModel.objects.get(
                user=user)
        except AttlasInsolvencyAuthConsultantsModel.DoesNotExist:
            raise serializers.ValidationError({
                'user': _('Asesor inválido. No existe un asesor con las iniciales proporcionadas.')
            })

        # 3. Verificar contraseña del asesor
        if not consultant.check_password(password):
            raise serializers.ValidationError({
                'password': _('Contraseña incorrecta para el asesor indicado.')
            })

        return {
            "user_id": auth_user.id,
            "document_number": data['document_number'],
            "consultant_id": consultant.id
        }


class AttlasInsolvencyAuthRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttlasInsolvencyAuthModel
        fields = ['document_number', 'birth_date']


class AttlasInsolvencyAuthConsultantsRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttlasInsolvencyAuthConsultantsModel
        fields = ['first_name', 'last_name', 'password']

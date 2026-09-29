# apps/project/api/platform/auth_platform/api/serializers.py

import secrets

from django.contrib.auth.hashers import check_password, make_password
from apps.common.utils.login_attempts import note_failure
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import (AttlasInsolvencyAuthConsultantsModel,
                      AttlasInsolvencyAuthModel, hash_value)

from apps.project.api.platform.insolvency_form.models import AttlasInsolvencyFormModel


# A usable hash performs the same password work for unknown consultants.
DUMMY_HASH = make_password(secrets.token_urlsafe(32))


class ClientSearchSerializer(serializers.Serializer):
    """Parámetros de búsqueda — nunca toca los campos cifrados directamente."""
    documentNumber = serializers.CharField()
    birthDate = serializers.DateField()


class RegisterSerializer(serializers.Serializer):
    documentNumber = serializers.CharField()
    birthDate = serializers.DateField()

    def validate_documentNumber(self, value):
        # Buscar por hash, no por valor cifrado
        if AttlasInsolvencyAuthModel.objects.filter(
            document_number_hash=hash_value(value)
        ).exists():
            raise serializers.ValidationError(
                ["Ya existe un usuario con este número de documento."]
            )
        return value

    def validate(self, data):
        # Verificar combinación document + birth_date
        dn_hash = hash_value(data['documentNumber'])
        bd_hash = hash_value(data['birthDate'].strftime('%Y-%m-%d'))
        if AttlasInsolvencyAuthModel.objects.filter(
            document_number_hash=dn_hash,
            birth_date_hash=bd_hash,
        ).exists():
            raise serializers.ValidationError(
                {"documentNumber": [
                    "Ya existe un usuario con este número de documento."]}
            )
        return data

    def create(self, validated_data):
        user = AttlasInsolvencyAuthModel.objects.create(
            document_number=validated_data['document_number'],
            birth_date=validated_data['birth_date'],
        )
        form, _ = AttlasInsolvencyFormModel.objects.get_or_create(
            user=user,
            defaults={'current_step': 1},
        )
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        return {
            'id':         str(user.id),
            'form_id':    str(form.id),
            'token':      str(access),
            'expires_in': int(access.lifetime.total_seconds()),
        }


class AttlasInsolvencyAuthSerializer(serializers.Serializer):
    document_number = serializers.CharField()
    birth_date = serializers.DateField()
    password = serializers.CharField()
    user = serializers.CharField()  # Iniciales del asesor

    def validate(self, data):
        doc_hash = hash_value(data['document_number'])
        birth_hash = hash_value(str(data['birth_date']))
        password = data['password']
        user = data['user'].strip().upper()
        request = self.context['request']

        auth_user = AttlasInsolvencyAuthModel.objects.filter(
            document_number_hash=doc_hash,
            birth_date_hash=birth_hash,
        ).first()
        consultant = AttlasInsolvencyAuthConsultantsModel.objects.filter(
            user=user,
        ).first()
        password_valid = (
            consultant.check_password(password) if consultant is not None
            else check_password(password, DUMMY_HASH)
        )

        if auth_user is None or consultant is None or not password_valid:
            note_failure(request, username=user, reason='attlas_login')
            raise serializers.ValidationError({
                'non_field_errors': [_('Invalid credentials.')]
            })

        return {
            "user_id": auth_user.id,
            "document_number": data['document_number'],
            "consultant_id": consultant.id,
            "user": user
        }


class AttlasInsolvencyAuthRegisterSerializer(serializers.ModelSerializer):

    def validate_document_number(self, value):
        if AttlasInsolvencyAuthModel.objects.filter(
            document_number_hash=hash_value(value)
        ).exists():
            raise serializers.ValidationError(
                ["Ya existe un usuario con este número de documento."]
            )
        return value

    def create(self, validated_data):
        user = AttlasInsolvencyAuthModel.objects.create(
            document_number=validated_data['document_number'],
            birth_date=validated_data['birth_date'],
        )
        form, _ = AttlasInsolvencyFormModel.objects.get_or_create(
            user=user,
            defaults={'current_step': 1},
        )
        refresh = RefreshToken.for_user(user)
        access  = refresh.access_token

        # Adjuntar al objeto para que to_representation lo lea
        user._form_id    = str(form.id)
        user._token      = str(access)
        user._expires_in = int(access.lifetime.total_seconds())
        return user

    def to_representation(self, instance):
        return {
            'id':         str(instance.id),
            'form_id':    instance._form_id,
            'token':      instance._token,
            'expires_in': instance._expires_in,
        }

    class Meta:
        model = AttlasInsolvencyAuthModel
        fields = ['document_number', 'birth_date']


class AttlasInsolvencyAuthConsultantsRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttlasInsolvencyAuthConsultantsModel
        fields = ['first_name', 'last_name', 'password']

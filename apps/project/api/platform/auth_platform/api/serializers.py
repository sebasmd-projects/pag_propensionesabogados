# apps/project/api/platform/auth_platform/api/serializers.py

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import (AttlasInsolvencyAuthConsultantsModel,
                      AttlasInsolvencyAuthModel, hash_value)

from apps.project.api.platform.insolvency_form.models import AttlasInsolvencyFormModel


class ClientSearchSerializer(serializers.Serializer):
    """Parámetros de búsqueda — nunca toca los campos cifrados directamente."""
    documentNumber = serializers.CharField()
    birthDate = serializers.DateField()


class ClientResponseSerializer(serializers.Serializer):
    """
    Forma la respuesta de búsqueda leyendo los campos cifrados del modelo
    y completando con los datos del formulario de insolvencia (step 2).
    """

    def to_representation(self, instance: AttlasInsolvencyAuthModel):
        form: AttlasInsolvencyFormModel | None = getattr(
            instance, 'insolvency_form', None
        )
        return {
            'id':         str(instance.id),
            'form_id':    str(form.id) if form else None,
            # Datos cifrados — se leen en claro desde la instancia ORM
            'documentNumber': instance.document_number,
            'birthDate':      instance.birth_date.isoformat()
            if instance.birth_date else None,
            # Datos personales guardados en el formulario de insolvencia (step 2)
            'firstName': form.debtor_first_name if form else '',
            'lastName':  form.debtor_last_name if form else '',
            'email':     form.debtor_email if form else '',
            'phone':     form.debtor_cell_phone if form else '',
            'address':   form.debtor_address if form else '',
        }


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
            document_number=validated_data['documentNumber'],
            birth_date=validated_data['birthDate'],
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

    def validate_documentNumber(self, value):
        if AttlasInsolvencyAuthModel.objects.filter(
            document_number_hash=hash_value(value)
        ).exists():
            raise serializers.ValidationError(
                ["Ya existe un usuario con este número de documento."]
            )
        return value

    def create(self, validated_data):
        user = AttlasInsolvencyAuthModel.objects.create(
            document_number=validated_data['documentNumber'],
            birth_date=validated_data['birthDate'],
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

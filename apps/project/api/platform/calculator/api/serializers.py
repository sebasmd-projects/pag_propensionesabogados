# apps/project/api/platform/calculator/serializers.py

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from apps.common.utils.models import hash_value
from apps.project.api.platform.auth_platform.models import AttlasInsolvencyAuthModel
from apps.project.api.platform.insolvency_form.models import AttlasInsolvencyFormModel

# ------------------------------------------------------------
# Validación para búsqueda por cédula y fecha de nacimiento
# ------------------------------------------------------------


class ClientSearchSerializer(serializers.Serializer):
    documentNumber = serializers.CharField(max_length=20)
    birthDate = serializers.DateField()

    def validate(self, data):
        doc_hash = hash_value(data['documentNumber'])
        birth_hash = hash_value(str(data['birthDate']))
        if not AttlasInsolvencyAuthModel.objects.filter(
            document_number_hash=doc_hash,
            birth_date_hash=birth_hash
        ).exists():
            raise serializers.ValidationError(
                _('No se encontró un usuario con esa cédula y fecha de nacimiento.')
            )
        return data


# ------------------------------------------------------------
# Serializador de salida (lectura) de los datos del cliente
# ------------------------------------------------------------
class ClientDataSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    documentNumber = serializers.CharField(
        source='user.document_number', read_only=True)
    firstName = serializers.CharField(source='debtor_first_name')
    lastName = serializers.CharField(source='debtor_last_name')
    email = serializers.EmailField(
        source='debtor_email', required=False, allow_blank=True)
    phone = serializers.CharField(
        source='debtor_cell_phone', required=False, allow_blank=True)
    address = serializers.CharField(
        source='debtor_address', required=False, allow_blank=True)
    birthDate = serializers.DateField(source='debtor_birth_date')

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = ['id', 'documentNumber', 'firstName',
                  'lastName', 'email', 'phone', 'address', 'birthDate']


# ------------------------------------------------------------
# Creación de cliente: incluye cédula y fecha (para Auth)
# ------------------------------------------------------------
class ClientCreateSerializer(serializers.ModelSerializer):
    documentNumber = serializers.CharField(write_only=True, max_length=20)
    birthDate = serializers.DateField(write_only=True)
    firstName = serializers.CharField(source='debtor_first_name')
    lastName = serializers.CharField(source='debtor_last_name')
    email = serializers.EmailField(
        source='debtor_email', required=False, allow_blank=True)
    phone = serializers.CharField(
        source='debtor_cell_phone', required=False, allow_blank=True)
    address = serializers.CharField(
        source='debtor_address', required=False, allow_blank=True)

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = ['documentNumber', 'birthDate', 'firstName',
                  'lastName', 'email', 'phone', 'address']

    def validate(self, data):
        doc_hash = hash_value(data['documentNumber'])
        birth_hash = hash_value(str(data['birthDate']))
        if AttlasInsolvencyAuthModel.objects.filter(
            document_number_hash=doc_hash,
            birth_date_hash=birth_hash
        ).exists():
            raise serializers.ValidationError({
                'documentNumber': _('Ya existe un usuario con esa cédula y fecha de nacimiento.')
            })
        return data

    def create(self, validated_data):
        from django.db import transaction

        documentNumber = validated_data.pop('documentNumber')
        birthDate = validated_data.pop('birthDate')

        with transaction.atomic():
            auth_user = AttlasInsolvencyAuthModel.objects.create(
                document_number=documentNumber,
                birth_date=birthDate
            )
            form = AttlasInsolvencyFormModel.objects.create(
                user=auth_user,
                debtor_document_number=documentNumber,
                debtor_birth_date=birthDate,
                current_step=1,
                **validated_data  # debtor_first_name, debtor_last_name, etc.
            )
        return form


# ------------------------------------------------------------
# Actualización de cliente (solo datos del formulario)
# ------------------------------------------------------------
class ClientUpdateSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(
        source='debtor_first_name', required=False)
    lastName = serializers.CharField(source='debtor_last_name', required=False)
    email = serializers.EmailField(
        source='debtor_email', required=False, allow_blank=True)
    phone = serializers.CharField(
        source='debtor_cell_phone', required=False, allow_blank=True)
    address = serializers.CharField(
        source='debtor_address', required=False, allow_blank=True)

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = ['firstName', 'lastName', 'email', 'phone', 'address']

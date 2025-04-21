# apps/project/api/platform/auth_platform/api/serializers.py

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import (AttlasInsolvencyAuthConsultantsModel,
                      AttlasInsolvencyAuthModel, hash_value)


class AttlasInsolvencyAuthSerializer(serializers.Serializer):
    document_number = serializers.CharField()
    birth_date = serializers.DateField()
    password = serializers.CharField()
    user = serializers.CharField()

    def validate(self, data):
        doc_hash = hash_value(data['document_number'])
        birth_hash = hash_value(str(data['birth_date']))
        password = data['password']
        user: str = data['user']

        try:
            record = AttlasInsolvencyAuthModel.objects.get(
                document_number_hash=doc_hash,
                birth_date_hash=birth_hash
            )

            consultant = AttlasInsolvencyAuthConsultantsModel.objects.get(
                user=user.upper()
            )

            if not consultant.check_password(password):
                raise serializers.ValidationError(_('Invalid code'))

            return {"user_id": record.id,  "document_number": data['document_number']}
        except AttlasInsolvencyAuthModel.DoesNotExist:
            raise serializers.ValidationError(_('Invalid credentials'))
        except AttlasInsolvencyAuthConsultantsModel.DoesNotExist:
            raise serializers.ValidationError(_('Invalid code'))


class AttlasInsolvencyAuthRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttlasInsolvencyAuthModel
        fields = ['document_number', 'birth_date']


class AttlasInsolvencyAuthConsultantsRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttlasInsolvencyAuthConsultantsModel
        fields = ['first_name', 'last_name', 'password']

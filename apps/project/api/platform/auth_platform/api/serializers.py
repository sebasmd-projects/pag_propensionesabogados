from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import AttlasInsolvencyAuthModel, hash_value


class AttlasInsolvencyAuthSerializer(serializers.Serializer):
    document_number = serializers.CharField()
    document_issue_date = serializers.DateField()
    birth_date = serializers.DateField()

    def validate(self, data):
        doc_hash = hash_value(data['document_number'])
        issue_hash = hash_value(str(data['document_issue_date']))
        birth_hash = hash_value(str(data['birth_date']))

        try:
            record = AttlasInsolvencyAuthModel.objects.get(
                document_number_hash=doc_hash,
                document_issue_date_hash=issue_hash,
                birth_date_hash=birth_hash
            )
            return {"user_id": record.id}
        except AttlasInsolvencyAuthModel.DoesNotExist:
            raise serializers.ValidationError(_('Invalid credentials'))


class AttlasInsolvencyAuthRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttlasInsolvencyAuthModel
        fields = ['document_number', 'document_issue_date', 'birth_date']

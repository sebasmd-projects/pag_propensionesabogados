#  apps/project/api/platform/insolvency_form/api/serializers.py

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import AttlasInsolvencyFormModel


class AttlasInsolvencyFormSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'id',
            'user',
            'form_data',
            'email_sent',
            'email_error'
        ]
        read_only_fields = [
            'id',
            'user',
            'email_sent',
            'email_error'
        ]

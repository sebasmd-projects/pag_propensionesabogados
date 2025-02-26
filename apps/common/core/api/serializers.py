from rest_framework.serializers import ModelSerializer

from ..models import ContactModel


class ConctactModelSerializer(ModelSerializer):
    class Meta:
        model = ContactModel
        exclude = [
            'created',
            'updated',
            'unique_id',
            'state'
        ]

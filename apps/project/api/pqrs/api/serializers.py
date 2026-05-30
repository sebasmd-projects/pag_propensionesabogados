from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from ..models import PQRSModel


class PQRSModelSerializer(ModelSerializer):

    request_type = serializers.ChoiceField(
        choices=PQRSModel.RequestTypeChoicesEN.choices,
        write_only=True,
    )

    def validate(self, data):
        # request_type → request_type_en + request_type_es
        if 'request_type' in data:
            rt = data.pop('request_type')
            data['request_type_en'] = rt
            data['request_type_es'] = rt

        return data
    
    class Meta:
        model = PQRSModel
        exclude = ['created', 'updated', 'history']
        extra_kwargs = {
            'request_type_en': {'required': False},
            'request_type_es': {'required': False},
        }
    

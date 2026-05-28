from rest_framework.serializers import ModelSerializer

from ..models import PQRSModel


class PQRSModelSerializer(ModelSerializer):
    class Meta:
        model = PQRSModel
        exclude = ['created', 'updated']

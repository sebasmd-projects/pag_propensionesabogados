from rest_framework.serializers import ModelSerializer, SerializerMethodField

from ..models import MainFAQModel, OtherFAQModel


class MainFAQModelSerializer(ModelSerializer):
    class Meta:
        model = MainFAQModel
        exclude = ['created', 'updated']


class OtherFAQModelSerializer(ModelSerializer):
    class Meta:
        model = OtherFAQModel
        exclude = ['created', 'updated']

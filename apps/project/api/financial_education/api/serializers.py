from rest_framework.serializers import ModelSerializer, SerializerMethodField

from ..models import FinancialEducationModel


class FinancialEducationModelSerializer(ModelSerializer):
    category = SerializerMethodField()
    category_en = SerializerMethodField()

    class Meta:
        model = FinancialEducationModel
        exclude = ['created', 'updated']

    def get_category(self, obj):
        """
        Devuelve el campo `category` como una lista.
        Si está vacío o es None, se retorna una lista vacía.
        """
        return obj.category.split(',') if obj.category else []

    def get_category_en(self, obj):
        """
        Devuelve el campo `category_en` como una lista.
        Si está vacío o es None, se retorna una lista vacía.
        """
        return obj.category_en.split(',') if obj.category_en else []

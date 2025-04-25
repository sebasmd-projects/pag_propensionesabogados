#  apps/project/api/platform/insolvency_form/api/serializers.py

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.utils.models import hash_value

from ..models import (AttlasInsolvencyAssetModel, AttlasInsolvencyAuthModel,
                      AttlasInsolvencyCreditorsModel,
                      AttlasInsolvencyFormModel, AttlasInsolvencyIncomeModel,
                      AttlasInsolvencyIncomeOtherModel,
                      AttlasInsolvencyJudicialProcessModel,
                      AttlasInsolvencyResourceItemModel,
                      AttlasInsolvencyResourceModel,
                      AttlasInsolvencyResourceTableModel,
                      AttlasInsolvencySignatureModel)


class StepMixin(serializers.ModelSerializer):
    class Meta:
        abstract = True
        read_only_fields = ('id', 'user', 'current_step')


class Step1Serializer(StepMixin):
    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'accept_legal_requirements',
            'accept_terms_and_conditions',
            'current_step',
            'id',
            'user',
        ]


class Step2Serializer(StepMixin):
    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'current_step',
            'debtor_address',
            'debtor_birth_date',
            'debtor_cell_phone',
            'debtor_document_number',
            'debtor_email',
            'debtor_expedition_city',
            'debtor_first_name',
            'debtor_is_merchant',
            'debtor_last_name',
            'debtor_sex',
            'id',
            'user',
        ]


class Step3Serializer(StepMixin):
    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'current_step',
            'debtor_statement_accepted',
            'id',
            'user',
        ]


class Step4Serializer(StepMixin):
    use_ai = serializers.BooleanField(
        default=False,
        help_text="Indica si el reporte debe pulirse con IA"
    )

    def update(self, instance, validated_data):
        validated_data.pop('use_ai', None)
        return super().update(instance, validated_data)

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'current_step',
            'debtor_cessation_report',
            'id',
            'use_ai',
            'user',
        ]


class CreditorSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttlasInsolvencyCreditorsModel
        exclude = ['form']
        extra_kwargs = {'id': {'read_only': False}}


class Step5Serializer(StepMixin):
    creditors = CreditorSerializer(
        many=True,
        source='creditors_form'
    )

    @transaction.atomic
    def update(self, instance, validated_data):
        creditors_data = validated_data.pop("creditors_form", [])

        # 1) Mapear objetos existentes
        existing = {obj.id: obj for obj in instance.creditors_form.all()}
        kept_ids = []

        # 2) Crear / actualizar
        for cred in creditors_data:
            cid = cred.pop("id", None)
            if cid and cid in existing:
                obj = existing[cid]
                for k, v in cred.items():
                    setattr(obj, k, v)
                obj.save()            # aquí tu pre_save ve el registro viejo y hace LOCAL
                kept_ids.append(cid)
            else:
                new_obj = AttlasInsolvencyCreditorsModel.objects.create(
                    form=instance, **cred
                )
                kept_ids.append(new_obj.id)

        # 3) Borrar sólo los que quedaron fuera
        to_delete = set(existing) - set(kept_ids)
        if to_delete:
            instance.creditors_form.filter(id__in=to_delete).delete()

        return instance

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'creditors',
            'current_step',
            'id',
            'user',
        ]


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttlasInsolvencyAssetModel
        exclude = ['form']
        extra_kwargs = {'id': {'read_only': False}}


class Step6Serializer(StepMixin):
    assets = AssetSerializer(
        many=True,
        source='asset_form'
    )

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'assets',
            'current_step',
            'id',
            'user',
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        assets = validated_data.pop('asset_form', [])
        instance.asset_form.all().delete()
        objs = [AttlasInsolvencyAssetModel(form=instance, **a) for a in assets]
        AttlasInsolvencyAssetModel.objects.bulk_create(objs)
        return instance


class JudicialProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttlasInsolvencyJudicialProcessModel
        exclude = ['form']
        extra_kwargs = {'id': {'read_only': False}}


class Step7Serializer(StepMixin):
    judicial_processes = JudicialProcessSerializer(
        many=True,
        source='judicial_form'
    )

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'current_step',
            'id',
            'judicial_processes',
            'user',
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        procs = validated_data.pop('judicial_form', [])
        instance.judicial_form.all().delete()
        objs = [
            AttlasInsolvencyJudicialProcessModel(form=instance, **p)
            for p in procs
        ]
        AttlasInsolvencyJudicialProcessModel.objects.bulk_create(objs)
        return instance


class IncomeOtherSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttlasInsolvencyIncomeOtherModel
        exclude = ['income']
        extra_kwargs = {'id': {'read_only': False}}


class IncomeSerializer(serializers.ModelSerializer):
    others = IncomeOtherSerializer(
        many=True,
        required=False,
        source='incomeother_income'
    )

    class Meta:
        model = AttlasInsolvencyIncomeModel
        exclude = ['form']
        extra_kwargs = {'id': {'read_only': False}}


class Step8Serializer(StepMixin):
    incomes = IncomeSerializer(
        many=True,
    )

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'current_step',
            'id',
            'incomes',
            'user',
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        incomes_data = validated_data.pop('incomes', [])
        instance.incomes.all().delete()

        for inc in incomes_data:
            others_data = inc.pop('incomeother_income', [])
            inc_obj = AttlasInsolvencyIncomeModel.objects.create(
                form=instance, **inc
            )
            objs = [
                AttlasInsolvencyIncomeOtherModel(income=inc_obj, **o)
                for o in others_data
            ]
            AttlasInsolvencyIncomeOtherModel.objects.bulk_create(objs)

        return instance


class Step9Serializer(StepMixin):
    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'current_step',
            'id',
            'partner_cell_phone',
            'partner_document_number',
            'partner_email',
            'partner_last_name',
            'partner_marital_status',
            'partner_name',
            'partner_relationship_duration',
            'user',
        ]


class ResourceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttlasInsolvencyResourceItemModel
        exclude = ['table']
        extra_kwargs = {'id': {'read_only': False}}


class ResourceTableSerializer(serializers.ModelSerializer):
    items = ResourceItemSerializer(many=True)

    class Meta:
        model = AttlasInsolvencyResourceTableModel
        exclude = ['resource']
        extra_kwargs = {'id': {'read_only': False}}


class ResourceSerializer(serializers.ModelSerializer):
    tables = ResourceTableSerializer(many=True)

    class Meta:
        model = AttlasInsolvencyResourceModel
        exclude = ['form']
        extra_kwargs = {'id': {'read_only': False}}


class Step10Serializer(StepMixin):
    resources = ResourceSerializer(many=True)

    class Meta:
        model = AttlasInsolvencyFormModel
        fields = [
            'current_step',
            'id',
            'resources',
            'user',
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        res_data = validated_data.pop('resources', [])
        instance.resources.all().delete()
        for r in res_data:
            tables = r.pop('tables', [])
            r_obj = AttlasInsolvencyResourceModel.objects.create(
                form=instance, **r
            )
            for t in tables:
                items = t.pop('items', [])
                t_obj = AttlasInsolvencyResourceTableModel.objects.create(
                    resource=r_obj, **t
                )
                objs = [
                    AttlasInsolvencyResourceItemModel(table=t_obj, **i)
                    for i in items
                ]
                AttlasInsolvencyResourceItemModel.objects.bulk_create(objs)
        return instance


class Step11Serializer(serializers.Serializer):
    signed = serializers.SerializerMethodField(read_only=True)
    signature = serializers.CharField(write_only=True, required=False)

    def get_signed(self, obj: AttlasInsolvencyFormModel) -> bool:
        # True si ya existe una firma asociada al formulario
        return AttlasInsolvencySignatureModel.objects.filter(form=obj).exists()

    def update(self, instance: AttlasInsolvencyFormModel, validated_data):
        sig_data = validated_data.get('signature', None)
        if sig_data:
            # crea o actualiza la firma
            AttlasInsolvencySignatureModel.objects.update_or_create(
                form=instance,
                defaults={'signature': sig_data}
            )
        return instance


class SignatureCreateSerializer(serializers.Serializer):
    cedula = serializers.CharField(write_only=True)
    signature = serializers.CharField(write_only=True)
    signed = serializers.SerializerMethodField(read_only=True)

    def get_signed(self, obj):
        # Siempre devolvemos true si llegamos aquí
        return True

    def validate(self, data):
        cedula_hash = hash_value(data['cedula'])
        try:
            auth = AttlasInsolvencyAuthModel.objects.get(
                document_number_hash=cedula_hash
            )
        except AttlasInsolvencyAuthModel.DoesNotExist:
            raise serializers.ValidationError({
                'cedula': 'No se encontró un usuario con esta cédula'
            })
        data['auth_user'] = auth
        return data

    def create(self, validated_data):
        auth_user = validated_data.pop('auth_user')
        sig_b64 = validated_data['signature']

        # Obtener o crear el formulario del usuario
        form, _ = AttlasInsolvencyFormModel.objects.get_or_create(user=auth_user)

        # Crear o actualizar la firma
        sig_obj, _ = AttlasInsolvencySignatureModel.objects.update_or_create(
            form=form,
            defaults={'signature': sig_b64}
        )
        return sig_obj

    def to_representation(self, instance):
        # Sólo devolvemos si quedó firmado
        return {'signed': True}

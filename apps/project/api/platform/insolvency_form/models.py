#  apps/project/api/platform/insolvency_form/models.py

import base64
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.utils.models import TimeStampedModel, hash_value
from apps.project.api.platform.auth_platform.models import \
    AttlasInsolvencyAuthModel


class AttlasInsolvencyFormModel(TimeStampedModel):
    # ---------- Step 1 -> 4 and Step 9 ----------
    class MARITAL_STATUS_OPTIONS(models.TextChoices):
        SINGLE = 'Soltero/a', 'Soltero/a'
        MARRIED = 'Casado/a', 'Casado/a'
        DIVORCED = 'Divorciado/a', 'Divorciado/a'
        WIDOWED = 'Viudo/a', 'Viudo/a'
        COHABITANT = 'Unión Libre', 'Unión Libre'
        DECLARATION = 'Declaración Marital', 'Declaración Marital'
        NN = 'No aplica', 'No aplica'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        AttlasInsolvencyAuthModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='insolvency_form'
    )
    current_step = models.PositiveSmallIntegerField(
        _('Current Step'),
        default=1
    )
    is_completed = models.BooleanField(
        _('Is Completed'),
        default=False
    )
    email_sent = models.BooleanField(default=False)
    email_error = models.TextField(blank=True)

    """
    Step 1: Legal Requirements
    """
    accept_legal_requirements = models.BooleanField(
        _('Accepted Legal Requirements'),
        default=False
    )
    accept_terms_and_conditions = models.BooleanField(
        _('Accepted Terms and Conditions'),
        default=False
    )

    """
    Step 2: Personal Data
    """
    debtor_document_number = models.CharField(
        _('Debtor Document Number'),
        max_length=20,
        blank=True,
        null=True
    )
    debtor_expedition_city = models.CharField(
        _('Debtor Expedition City'),
        max_length=100,
        blank=True,
        null=True
    )
    debtor_first_name = models.CharField(
        _('Debtor First Name'),
        max_length=100,
        blank=True,
        null=True
    )
    debtor_last_name = models.CharField(
        _('Debtor Last Name'),
        max_length=100,
        blank=True,
        null=True
    )
    debtor_is_merchant = models.BooleanField(
        _('Debtor is Merchant'),
        default=False
    )
    debtor_cell_phone = models.CharField(
        _('Debtor Cell Phone'),
        max_length=20,
        blank=True,
        null=True
    )
    debtor_email = models.EmailField(
        _('Debtor Email'),
        max_length=100,
        blank=True,
        null=True
    )
    debtor_birth_date = models.DateField(
        _('Debtor Birth Date'),
        blank=True,
        null=True
    )
    debtor_address = models.CharField(
        _('Debtor Location/Address'),
        max_length=100,
        blank=True,
        null=True
    )
    debtor_sex = models.CharField(
        _('Sex'),
        max_length=10,
        blank=True,
        null=True,
    )
    """
    Step 3: Cessation of Payments Acceptance
    """
    debtor_statement_accepted = models.BooleanField(
        _('Debtor Statement Accepted'),
        default=False
    )
    """
    Step 4: Cessation of Payments Report
    """
    debtor_cessation_report = models.TextField(
        _('Debtor Cessation Report'),
        blank=True,
        null=True
    )

    """
    Step 5 -> 8: Creditors, Assets, Judicial Processes and Income
    handled through related reverse models
    """

    """
    Step 9: Partner
    """
    partner_marital_status = models.CharField(
        _('Marital Status'),
        max_length=100,
        blank=True,
        null=True,
        choices=MARITAL_STATUS_OPTIONS.choices
    )
    partner_document_number = models.CharField(
        _('Partner Document Number'),
        max_length=20,
        blank=True,
        null=True
    )
    partner_name = models.CharField(
        _('Partner Name'),
        max_length=100,
        blank=True,
        null=True
    )
    partner_last_name = models.CharField(
        _('Partner Last Name'),
        max_length=100,
        blank=True,
        null=True
    )
    partner_email = models.EmailField(
        _('Partner Email'),
        max_length=100,
        blank=True,
        null=True
    )
    partner_cell_phone = models.CharField(
        _('Partner Phone'),
        max_length=20,
        blank=True,
        null=True
    )
    partner_relationship_duration = models.IntegerField(
        _('Partner Relationship Duration (months)'),
        blank=True,
        default=0,
    )

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user and not self.user:
            self.user = user

        if self.debtor_document_number and not self.user:
            document_hash = hash_value(self.debtor_document_number)
            self.user = AttlasInsolvencyAuthModel.objects.filter(
                document_number=document_hash
            ).first()

        super().save(*args, **kwargs)

    def __str__(self):

        if self.debtor_first_name and self.debtor_last_name:
            return f"{self.user.document_number} - {self.debtor_first_name} {self.debtor_last_name}"

        return f"{self.user.document_number}"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_form'
        verbose_name = _('Attlas Insolvency Form')
        verbose_name_plural = _('Attlas Insolvency Forms')
        ordering = ['-created']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='one_form_per_user'
            )
        ]


class AttlasInsolvencyCreditorsModel(TimeStampedModel):
    # ---------- Step 5: Creditors ----------
    class NATURE_OPTIONS(models.TextChoices):
        CDL = 'CRÉDITO DE LIBRANZA', 'Crédito de Libranza'
        CN = 'CRÉDITO DE NOMINA', 'Crédito de Nómina'
        CH = 'CRÉDITO HIPOTECARIO', 'Crédito Hipotecario'
        CGM = 'CRÉDITO DE GARANTÍA MOBILIARIA', 'Crédito de Garantía Mobiliaria'
        CFT = 'CRÉDITO FISCAL O TRIBUTARIO', 'Crédito Fiscal o Tributario'
        CLI = 'CRÉDITO DE LIBRE INVERSION', 'Crédito de Libre Inversión'
        CP = 'CRÉDITO PERSONAL', 'Crédito Personal'
        CM = 'CRÉDITO COMERCIAL', 'Crédito Comercial'
        CR = 'CRÉDITO ROTATIVO', 'Crédito Rotativo'
        CEE = 'CRÉDITO EDUCATIVO O DE ESTUDIO', 'Crédito Educativo o de Estudio'
        CC = 'CRÉDITO DE CONSUMO', 'Crédito de Consumo'
        OTRO = 'OTRO', 'Otro'

    class CONSANGUINITY_OPTIONS(models.TextChoices):
        NN = 'NN', 'No tengo parentesco'
        FIC = '1C', '1° consanguíneo: Compañero/a permanente, Padres e Hijos'
        SEC = '2C', '2° consanguíneo: Abuelos, Nietos y Hermanos'
        THC = '3C', '3° consanguíneo: Tíos y Sobrinos'
        FOC = '4C', '4° consanguíneo: Primos y Sobrinos (nietos)'
        FIA = '1A', '1° afinidad: Suegros y Yerno/Nuera'
        SCA = '2A', '2° afinidad: Abuelos, Nietos y Hermanos del compañero/a permanente'
        FICIV = '1CIV', '1° civil: Hijos adoptados y Padres Adoptivos'

    form = models.ForeignKey(
        AttlasInsolvencyFormModel,
        on_delete=models.CASCADE,
        related_name='creditors_form'
    )
    creditor = models.CharField(
        _('Creditor'),
        max_length=100,
        blank=True,
        null=True
    )
    nit = models.CharField(
        _('NIT'),
        max_length=20,
        blank=True,
        null=True
    )
    creditor_contact = models.CharField(
        _('Creditor Contact'),
        max_length=100,
        blank=True,
        null=True
    )
    nature_type = models.CharField(
        _('Nature Type'),
        max_length=100,
        choices=NATURE_OPTIONS.choices
    )
    other_nature = models.CharField(
        _('Other Nature'),
        max_length=100,
        blank=True,
        null=True
    )
    personal_credit_interest_rate = models.DecimalField(
        _('Personal Credit Interest Rate'),
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    personal_consanguinity = models.CharField(
        _('Personal Consanguinity'),
        max_length=100,
        choices=CONSANGUINITY_OPTIONS.choices,
        blank=True,
        null=True
    )
    guarantee = models.CharField(
        _('Guarantee'),
        max_length=100,
        blank=True,
        null=True
    )
    capital_value = models.DecimalField(
        _('Capital Value'),
        max_digits=20,
        decimal_places=2,
        blank=True,
        null=True
    )
    days_overdue = models.IntegerField(
        _('Days Overdue'),
        blank=True,
        null=True
    )
    credit_classification = models.CharField(
        _('Credit Classification'),
        max_length=100,
        default='5',
        blank=True,
        null=True
    )

    def clean(self):
        super().clean()

        if self.nature_type == self.NATURE_OPTIONS.OTRO and not self.other_nature:
            raise ValidationError(
                {
                    'other_nature': _("This field is required when 'Other' is selected.")
                }
            )

        if self.nature_type == self.NATURE_OPTIONS.CP and not self.personal_credit_interest_rate:
            raise ValidationError(
                {
                    'personal_credit_interest_rate': _("This field is required when 'Personal Credit' is selected.")
                }
            )

        if self.nature_type == self.NATURE_OPTIONS.CP and not self.personal_consanguinity:
            raise ValidationError(
                {
                    'personal_consanguinity': _("This field is required when 'Personal Credit' is selected.")
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.creditor} - {self.nature_type}" if self.nature_type else self.creditor

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_creditors'
        verbose_name = _('Attlas Insolvency Creditors')
        verbose_name_plural = _('Attlas Insolvency Creditors')
        ordering = ['-created']


class AttlasInsolvencyAssetModel(TimeStampedModel):
    # ---------- Step 6: Assets ----------
    class ASSET_TYPE_OPTIONS(models.TextChoices):
        IM = 'INMUEBLE', 'Inmueble'
        MM = 'MUEBLE', 'Mueble'

    form = models.ForeignKey(
        AttlasInsolvencyFormModel,
        on_delete=models.CASCADE,
        related_name='asset_form'
    )
    asset_type = models.CharField(
        _('Asset Type'),
        max_length=100,
        choices=ASSET_TYPE_OPTIONS.choices
    )
    name = models.CharField(
        _('Description/Name'),
        max_length=100
    )
    identification = models.CharField(
        _('Identification'),
        max_length=100
    )
    lien = models.CharField(
        _('Lien'),
        max_length=100,
        blank=True,
        null=True
    )
    affectation = models.CharField(
        _('Affectation'),
        max_length=100,
        blank=True,
        null=True
    )
    legal_measure = models.JSONField(
        _('Legal Measure'),
        blank=True,
        null=True
    )
    patrimonial_society = models.CharField(
        _('Patrimonial Society'),
        max_length=100,
        blank=True,
        null=True
    )
    commercial_value = models.DecimalField(
        _('Commercial Value'),
        max_digits=20,
        decimal_places=2
    )
    exclusion = models.BooleanField(
        _('Exclusion'),
        default=False
    )

    def __str__(self):
        return f"{self.asset_type} - {self.name}"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_asset'
        verbose_name = _('Attlas Insolvency Asset')
        verbose_name_plural = _('Attlas Insolvency Assets')
        ordering = ['-created']


class AttlasInsolvencyJudicialProcessModel(TimeStampedModel):
    # --------- Step 7: Judicial Process ----------
    form = models.ForeignKey(
        AttlasInsolvencyFormModel,
        on_delete=models.CASCADE,
        related_name='judicial_form'
    )
    affectation = models.CharField(
        _('Affectation'),
        max_length=100
    )
    court = models.TextField(
        _('Court'),
    )
    description = models.TextField(
        _('Description')
    )
    case_code = models.CharField(
        _('Case Code'),
        max_length=100
    )
    process_status = models.JSONField(
        _('Process Status'),
        max_length=100
    )

    def __str__(self):
        return f"{self.affectation} - {self.court} - {self.case_code}"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_judicial_process'
        verbose_name = _('Attlas Insolvency Judicial Process')
        verbose_name_plural = _('Attlas Insolvency Judicial Processes')
        ordering = ['-created']


class AttlasInsolvencyIncomeModel(TimeStampedModel):
    # ---------- Step 8: Income ----------
    class IncomeType(models.TextChoices):
        SALARY = 'SALARIO', 'Salario'
        INDEPENDENT = 'INDEPENDIENTE', 'Independiente'
        PENSIONER = 'PENSIONADO', 'Pensionado'
        UNEMPLOYED = 'DESEMPLEADO', 'Desempleado'
        OTHER = 'OTRO', 'Otro'

    form = models.ForeignKey(
        AttlasInsolvencyFormModel,
        on_delete=models.CASCADE,
        related_name='incomes'
    )
    type = models.CharField(
        _('Income Type'),
        max_length=20,
        choices=IncomeType.choices
    )
    amount = models.DecimalField(
        _('Amount'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount}"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_income'
        verbose_name = _('Attlas Insolvency Income')
        verbose_name_plural = _('Attlas Insolvency Incomes')
        ordering = ['-created']


class AttlasInsolvencyIncomeOtherModel(TimeStampedModel):
    # ---------- Step 8: Income Other ----------
    income = models.ForeignKey(
        AttlasInsolvencyIncomeModel,
        on_delete=models.CASCADE,
        related_name='incomeother_income'
    )
    detail = models.CharField(
        _('Detail'),
        max_length=255
    )
    amount = models.DecimalField(
        _('Amount'),
        max_digits=15,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.detail} - {self.amount}"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_income_other'
        verbose_name = _('Attlas Insolvency Income Other')
        verbose_name_plural = _('Attlas Insolvency Incomes Other')
        ordering = ['-created']


class AttlasInsolvencyResourceModel(TimeStampedModel):
    # ---------- Step 10: Resources ----------
    form = models.ForeignKey(
        AttlasInsolvencyFormModel,
        on_delete=models.CASCADE,
        related_name='resources',
        verbose_name=_('Insolvency Form')
    )
    has_food_obligation = models.BooleanField(
        _('Has Food Obligation'),
        default=False
    )
    proposed_monthly_value = models.DecimalField(
        _('Proposed Monthly Value'),
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True
    )
    children_count = models.IntegerField(
        _('Children Count'),
        default=0
    )

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_resource'
        verbose_name = _('Attlas Insolvency Resource')
        verbose_name_plural = _('Attlas Insolvency Resources')
        ordering = ['-created']

    def __str__(self):
        return f"{self.form} – Resources"


class AttlasInsolvencyResourceTableModel(TimeStampedModel):
    """
    Cada “tabla” corresponde a un grupo familiar (deudor, cónyuge, hijo, etc.)
    """
    class RelationshipChoices(models.TextChoices):
        DEBTOR = 'DEUDOR', 'DEUDOR'
        HUSBAND = 'ESPOSO', 'ESPOSO'
        WIFE = 'ESPOSA', 'ESPOSA'
        PERMANENT_PARTNER = 'PAREJA PERMANENTE', 'PAREJA PERMANENTE'
        SON = 'HIJO', 'HIJO'
        DAUGHTER = 'HIJA', 'HIJA'
        MOTHER = 'MADRE', 'MADRE'
        FATHER = 'PADRE', 'PADRE'
        OTHER = 'OTRO', 'OTRO'

    class GenderChoices(models.TextChoices):
        MALE = 'MASCULINO', _('Male')
        FEMALE = 'FEMENINO', _('Female')

    resource = models.ForeignKey(
        AttlasInsolvencyResourceModel,
        on_delete=models.CASCADE,
        related_name='tables',
        verbose_name=_('Resource')
    )
    title = models.CharField(
        _('Table Title'),
        max_length=100
    )
    relationship = models.CharField(
        _('Relationship'),
        max_length=20,
        choices=RelationshipChoices.choices
    )
    disability = models.BooleanField(
        _('Has Disability'),
        default=False
    )
    age = models.IntegerField(
        _('Age'),
        blank=True,
        null=True
    )
    gender = models.CharField(
        _('Gender'),
        max_length=10,
        choices=GenderChoices.choices,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_resource_table'
        verbose_name = _('Attlas Insolvency Resource Table')
        verbose_name_plural = _('Attlas Insolvency Resource Tables')
        ordering = ['-created']

    def __str__(self):
        return f"{self.get_relationship_display()} – {self.title}"


class AttlasInsolvencyResourceItemModel(TimeStampedModel):
    """
    Cada fila de gastos dentro de una tabla (label/legal/value)
    """
    table = models.ForeignKey(
        AttlasInsolvencyResourceTableModel,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Resource Table')
    )
    label = models.CharField(
        _('Expense Label'),
        max_length=150
    )
    legal_support = models.CharField(
        _('Legal Support'),
        max_length=255,
        blank=True
    )
    value = models.DecimalField(
        _('Value'),
        max_digits=15,
        decimal_places=2,
        default=0.00
    )

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_resource_item'
        verbose_name = _('Attlas Insolvency Resource Item')
        verbose_name_plural = _('Attlas Insolvency Resource Items')
        ordering = ['-created']

    def __str__(self):
        return f"{self.label}: {self.value}"


class AttlasInsolvencySignatureModel(TimeStampedModel):
    # ---------- Step11: Signature ----------
    form = models.ForeignKey(
        AttlasInsolvencyFormModel,
        on_delete=models.SET_NULL,
        related_name='signature_form',
        null=True,
    )
    signature = models.TextField(
        _('Signature'),
        blank=True,
        null=True
    )
    client_ip = models.CharField(
        _('Client IP'),
        max_length=100,
        blank=True,
        null=True
    )
    user_agent = models.CharField(
        _('User Agent'),
        max_length=255,
        blank=True,
        null=True
    )

    def get_signature(self):
        return ContentFile(
            base64.b64decode(self.signature.split(',')[1]),
            name=f"{self.form.debtor_document_number}_signature.png"
        )

    def __str__(self):
        if self.form.debtor_first_name and self.form.debtor_last_name:
            return f"{self.form.debtor_first_name} {self.form.debtor_last_name} - {self.form.debtor_document_number}"
        return f"signature"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_signature'
        verbose_name = _('Attlas Insolvency Signature')
        verbose_name_plural = _('Attlas Insolvency Signatures')
        ordering = ['-created']

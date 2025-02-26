from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.utils.models import TimeStampedModel


class PQRSModel(TimeStampedModel):
    class RequestTypeChoicesEN(models.TextChoices):
        ACCESS = 'ACCESS', 'Access'
        UPDATE = 'UPDATE', 'Update'
        RECTIFICATION = 'RECTIFICATION', 'Rectification'
        DELETE = 'DELETE', 'Delete'
        REQUEST = 'REQUEST', 'Request'
        CLAIM = 'CLAIM', 'Claim'
        COMPLAINT = 'COMPLAINT', 'Complaint'
        INQUIRY = 'INQUIRY', 'Inquiry'
        OTHER = 'OTHER', 'Other'

    class RequestTypeChoicesES(models.TextChoices):
        ACCESS = 'ACCESS', 'Acceso'
        UPDATE = 'UPDATE', 'Actualización'
        RECTIFICATION = 'RECTIFICATION', 'Rectificación'
        DELETE = 'DELETE', 'Supresión'
        REQUEST = 'REQUEST', 'Petición'
        CLAIM = 'CLAIM', 'Reclamo'
        COMPLAINT = 'COMPLAINT', 'Queja'
        INQUIRY = 'INQUIRY', 'Consulta'
        OTHER = 'OTHER', 'Otro'

    class IDTypeChoices(models.TextChoices):
        CC = 'CC', _('CC')
        CE = 'CE', _('CE')
        PA = 'PA', _('PA')
        OTHER = 'OTHER', _('Other')

    request_type_en = models.CharField(
        _('request type'),
        max_length=255,
        choices=RequestTypeChoicesEN.choices,
        default=RequestTypeChoicesEN.OTHER,
        blank=True,
        null=True
    )

    request_type_es = models.CharField(
        _('request type'),
        max_length=255,
        choices=RequestTypeChoicesEN.choices,
        default=RequestTypeChoicesEN.OTHER,
        blank=True,
        null=True
    )

    is_legal_entity = models.BooleanField(
        _('is legal entity'),
        default=False
    )

    company_name = models.CharField(
        _('company name'),
        max_length=255,
        blank=True,
        null=True
    )

    nit = models.CharField(
        _('NIT'),
        max_length=255,
        blank=True,
        null=True
    )

    legal_representative = models.CharField(
        _('legal representative'),
        max_length=255,
        blank=True,
        null=True
    )

    name = models.CharField(
        _('name'),
        max_length=255
    )

    surname = models.CharField(
        _('surname'),
        max_length=255
    )

    id_type = models.CharField(
        _('ID type'),
        blank=True,
        null=True,
        max_length=255,
        choices=IDTypeChoices.choices,
        default=IDTypeChoices.CC
    )

    id_number = models.CharField(
        _('ID number'),
        max_length=255
    )

    country = models.CharField(
        _('country'),
        max_length=255
    )

    city = models.CharField(
        _('city'),
        max_length=255
    )

    addres = models.CharField(
        _('addres'),
        max_length=255
    )

    email = models.EmailField(
        _('email'),
        max_length=255,
    )

    cell_prefix = models.CharField(
        _('cell prefix'),
        max_length=10
    )

    cellphone = models.CharField(
        _('cellphone'),
        max_length=15
    )

    documents = models.URLField(
        _('documents'),
        blank=True,
        null=True
    )

    description = models.TextField(
        _('description'),
    )

    contact_methods = models.CharField(
        _('contact methods'),
        blank=True,
        null=True,
        max_length=255
    )

    contact_email = models.EmailField(
        _('contact email'),
        max_length=255,
        blank=True,
        null=True
    )

    contact_cell_prefix = models.CharField(
        _('contact cell prefix'),
        max_length=10,
        blank=True,
        null=True
    )

    contact_cellphone = models.CharField(
        _('contact cellphone'),
        max_length=15,
        blank=True,
        null=True
    )

    contact_phone_prefix = models.CharField(
        _('contact phone prefix'),
        max_length=10,
        blank=True,
        null=True
    )

    contact_phone = models.CharField(
        _('contact phone'),
        max_length=15,
        blank=True,
        null=True
    )

    terms_accepted = models.BooleanField(
        _('terms accepted'),
        default=False
    )

    class Meta:
        db_table = 'apps_project_api_pqrs'
        verbose_name = _('PQRS')
        verbose_name_plural = _('PQRS')
        ordering = ['-created']

    def __str__(self):
        return self.name + ' ' + self.surname

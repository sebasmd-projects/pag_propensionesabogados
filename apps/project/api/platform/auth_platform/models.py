# apps/project/api/platform/auth_platform/models.py

import uuid

from auditlog.registry import auditlog
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import (EncryptedCharField,
                                           EncryptedDateField)

from apps.common.utils.models import TimeStampedModel, hash_value


class AttlasInsolvencyAuthConsultantsModel(TimeStampedModel):
    id = models.UUIDField(
        'ID',
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        serialize=False,
        editable=False
    )

    first_name = models.CharField(
        _('first name'),
        max_length=100,
    )

    last_name = models.CharField(
        _('last name'),
        max_length=100,
    )

    user = models.CharField(
        _('user'),
        max_length=15,
        unique=True,
        blank=True,
        null=True
    )

    password = models.CharField(
        _("password"),
        max_length=128,
        blank=True,
        null=True
    )

    @property
    def get_initials(self):
        """Versión concisa de la función de iniciales"""
        return ''.join([name[0].upper() for name in self.first_name.split() + self.last_name.split() if name])

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.user} {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith("argon2$"):
            self.password = make_password(self.password)
        if not self.user:
            self.user = self.get_initials
        self.first_name = self.first_name.upper()
        self.last_name = self.last_name.upper()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_consultants'
        verbose_name = _('ATTLAS Insolvency | Consultants')
        verbose_name_plural = _('ATTLAS Insolvency | Consultants')
        ordering = ['-created']


class AttlasInsolvencyAuthModel(TimeStampedModel):
    id = models.UUIDField(
        'ID',
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        serialize=False,
        editable=False
    )

    # Campos cifrados
    document_number = EncryptedCharField(
        max_length=100
    )

    birth_date = EncryptedDateField()

    document_number_hash = models.CharField(max_length=64, db_index=True)

    birth_date_hash = models.CharField(max_length=64, db_index=True)

    @property
    def is_authenticated(self):
        return True

    def save(self, *args, **kwargs):
        self.document_number_hash = hash_value(self.document_number)
        self.birth_date_hash = hash_value(self.birth_date.strftime('%Y-%m-%d'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.document_number} - {self.birth_date}"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_auth'
        verbose_name = _('Attlas Insolvency Auth')
        verbose_name_plural = _('Attlas Insolvency Auths')
        unique_together = (
            ('document_number_hash', 'birth_date_hash'),
        )
        ordering = ['-created']


auditlog.register(
    AttlasInsolvencyAuthModel,
    serialize_data=True
)

auditlog.register(
    AttlasInsolvencyAuthConsultantsModel,
    serialize_data=True
)

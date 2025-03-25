# apps/project/api/platform/auth_platform/models.py

import uuid

from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import (EncryptedCharField,
                                           EncryptedDateField)

from apps.common.utils.models import TimeStampedModel, hash_value

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
    document_issue_date = EncryptedDateField()
    birth_date = EncryptedDateField()

    # Campos hash (para búsquedas)
    document_number_hash = models.CharField(max_length=64, db_index=True)
    document_issue_date_hash = models.CharField(max_length=64, db_index=True)
    birth_date_hash = models.CharField(max_length=64, db_index=True)

    def save(self, *args, **kwargs):
        self.document_number_hash = hash_value(self.document_number)

        self.document_issue_date_hash = hash_value(
            str(self.document_issue_date)
        )

        self.birth_date_hash = hash_value(str(self.birth_date))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.document_number} - {self.id}"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_auth'
        verbose_name = _('Attlas Insolvency Auth')
        verbose_name_plural = _('Attlas Insolvency Auths')
        ordering = ['-created']


auditlog.register(
    AttlasInsolvencyAuthModel,
    serialize_data=True
)

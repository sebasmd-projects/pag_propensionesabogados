#  apps/project/api/platform/insolvency_form/models.py

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.utils.models import TimeStampedModel, hash_value
from apps.project.api.platform.auth_platform.models import \
    AttlasInsolvencyAuthModel

from django.db.models.signals import post_save

from .signals import send_insolvency_email


class AttlasInsolvencyFormModel(TimeStampedModel):
    id = models.UUIDField(
        'ID',
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        serialize=False,
        editable=False
    )

    user = models.ForeignKey(
        AttlasInsolvencyAuthModel,
        on_delete=models.SET_NULL,
        related_name='attlas_insolvency_forms',
        null=True,
        blank=True,
    )

    form_data = models.JSONField(
        _('Form Data'),
        blank=True,
        null=True
    )

    email_sent = models.BooleanField(default=False)

    email_error = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.form_data and 'document_number' in self.form_data:
            document_number = self.form_data['document_number']
            hashed_doc = hash_value(document_number)
            user = AttlasInsolvencyAuthModel.objects.filter(
                document_number_hash=hashed_doc
            ).first()
            self.user = user
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.document_number} - {self.id}"

    class Meta:
        db_table = 'apps_project_api_platform_attlas_insolvency_form'
        verbose_name = 'Attlas Insolvency Form'
        verbose_name_plural = 'Attlas Insolvency Forms'
        ordering = ['-created']


post_save.connect(
    send_insolvency_email,
    sender=AttlasInsolvencyFormModel
)

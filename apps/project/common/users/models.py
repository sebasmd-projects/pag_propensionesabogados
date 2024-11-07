import uuid

from auditlog.registry import auditlog
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.utils.models import TimeStampedModel


class UserModel(TimeStampedModel, AbstractUser):
    id = models.UUIDField(
        'ID',
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        serialize=False,
        editable=False
    )

    REQUIRED_FIELDS = [
        'email',
        'first_name',
        'last_name'
    ]

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
        self.username = self.username.lower()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_full_name()}"

    class Meta:
        db_table = 'apps_project_common_users_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        unique_together = [['username', 'email']]


auditlog.register(
    UserModel,
    serialize_data=True
)

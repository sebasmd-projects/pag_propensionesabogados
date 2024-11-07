from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.project.common.users.models import UserModel


class UserLoginAttemptModel(models.Model):
    user = models.OneToOneField(UserModel, on_delete=models.CASCADE)
    attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} - {self.attempts} - {self.last_attempt}"

    class Meta:
        db_table = 'apps_project_common_account_userloginattempt'
        verbose_name = _('User Login Attempt')
        verbose_name_plural = _('User Login Attempts')


auditlog.register(
    UserLoginAttemptModel,
    serialize_data=True
)

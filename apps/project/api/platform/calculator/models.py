# apps/project/api/platform/calculator/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.utils.models import TimeStampedModel

class InterestRateModel(TimeStampedModel):
    """Tasa de usura vigente (capturada manual o automáticamente)"""
    rate = models.DecimalField(
        _('Tasa de usura (%)'),
        max_digits=6,
        decimal_places=2,
        help_text='Tasa efectiva anual (por ejemplo 45.27)'
    )
    effective_date = models.DateField(
        _('Fecha de vigencia'),
        auto_now_add=True,
        help_text='Fecha desde la cual aplica esta tasa'
    )

    class Meta:
        db_table = 'apps_platform_calculator_interest_rate'
        verbose_name = _('Tasa de usura')
        verbose_name_plural = _('Tasas de usura')
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.rate}% (desde {self.effective_date})"
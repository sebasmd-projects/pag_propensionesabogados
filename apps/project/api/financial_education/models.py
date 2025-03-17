from django.db import models
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from apps.common.utils.models import TimeStampedModel


class FinancialEducationModel(TimeStampedModel):
    title = models.CharField(
        _('title'),
        max_length=255,
        blank=True,
        null=True
    )

    title_en = models.CharField(
        _('title en'),
        max_length=255,
        blank=True,
        null=True
    )

    video_url = models.URLField(
        _('video url'),
        max_length=255,
        blank=True,
        null=True
    )

    category = models.CharField(
        _('category'),
        max_length=255,
        blank=True,
        null=True
    )

    category_en = models.CharField(
        _('category en'),
        max_length=255,
        blank=True,
        null=True
    )

    description = CKEditor5Field(
        _('description'),
        blank=True,
        null=True
    )

    description_en = CKEditor5Field(
        _('description en'),
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'apps_project_api_financial_education'
        verbose_name = _('financial education')
        verbose_name_plural = _('financial educations')
        ordering = ['default_order', 'created']

    def save(self, *args, **kwargs):
        for field in ['category', 'category_en']:
            if value := getattr(self, field):
                categories = [cat.strip().replace(' ', '_') for cat in value.split(',')]
                setattr(self, field, ','.join(categories))
                

        for field in ['description', 'description_en']:
            if getattr(self, field) in ["<p>&nbsp;</p>", "\u003Cp\u003E&nbsp;\u003C/p\u003E"]:
                setattr(self, field, None)

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.video_url

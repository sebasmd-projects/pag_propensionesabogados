from django.db import models
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from apps.common.utils.models import TimeStampedModel


class MainFAQModel(TimeStampedModel):
    question = models.CharField(
        _('question'),
        max_length=255
    )

    answer = models.TextField(
        _('answer')
    )

    class Meta:
        db_table = 'apps_project_api_mainfaq'
        verbose_name = _('Main FAQ')
        verbose_name_plural = _('Main FAQs')
        ordering = ['default_order', '-created']

    def __str__(self):
        return self.question


class OtherFAQModel(TimeStampedModel):
    question = models.CharField(
        _('question'),
        max_length=255
    )

    short_answer = models.CharField(
        _('short answer'),
        max_length=100
    )

    answer = CKEditor5Field(
        _('answer')
    )

    class Meta:
        db_table = 'apps_project_api_otherfaq'
        verbose_name = _('Other FAQ')
        verbose_name_plural = _('Other FAQs')
        ordering = ['default_order', '-created']

    def __str__(self):
        return self.question

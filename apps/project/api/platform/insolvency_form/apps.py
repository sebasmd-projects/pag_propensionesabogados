# apps/project/api/platform/insolvency_form/apps.py

from django.apps import AppConfig
from django.db.models.signals import post_save, pre_save


class InsolvencyFormConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.project.api.platform.insolvency_form'

    def ready(self):
        from .models import (
            AttlasInsolvencyFormModel,
            AttlasInsolvencyCreditorsModel,
        )
        from .signals import send_insolvency_email, save_nit_and_contact

        post_save.connect(
            send_insolvency_email,
            sender=AttlasInsolvencyFormModel,
            weak=False,
        )

        pre_save.connect(
            save_nit_and_contact,
            sender=AttlasInsolvencyCreditorsModel,
            weak=False,
        )

from django.apps import AppConfig


class CaseManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.project.case_manager'
    label = 'case_manager'

    def ready(self):
        from . import checks  # noqa: F401

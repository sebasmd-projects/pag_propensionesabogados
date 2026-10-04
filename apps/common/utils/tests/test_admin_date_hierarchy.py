# apps/common/utils/tests/test_admin_date_hierarchy.py
from django.contrib import admin
from django.db import models
from django.test import SimpleTestCase


class AdminDateHierarchyTests(SimpleTestCase):
    def test_no_date_hierarchy_on_datetime_fields(self):
        """
        Ningun ModelAdmin puede usar ``date_hierarchy`` sobre un DateTimeField.

        Con ``USE_TZ=True`` Django agrupa por fecha con ``CONVERT_TZ`` en MySQL.
        Produccion corre en hosting compartido (cPanel) donde las tablas de
        zonas horarias de MySQL no se pueden cargar, asi que CONVERT_TZ
        devuelve NULL y el listado revienta con ``ValueError: Database returned
        an invalid datetime value. Are time zone definitions for your database
        installed?``. SQLite no lo detecta en desarrollo, por eso este test.
        Para filtrar por fecha usar ``list_filter`` (rangos simples) o un
        DateField.
        """
        offenders = []
        for model, model_admin in admin.site._registry.items():
            name = model_admin.date_hierarchy
            if not name:
                continue
            field = model._meta.get_field(name)
            if isinstance(field, models.DateTimeField):
                offenders.append(f'{model_admin.__class__.__name__}.{name}')
        self.assertEqual(offenders, [])

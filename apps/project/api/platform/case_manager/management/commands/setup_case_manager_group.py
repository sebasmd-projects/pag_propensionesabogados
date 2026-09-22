"""
Crea el grupo del gestor con los permisos que necesita.

Se ejecuta una vez por entorno, despues de migrar. Es idempotente: volver a
correrlo no duplica nada ni quita permisos concedidos a mano.
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.project.api.platform.case_manager.access import GESTOR_GROUP
from apps.project.api.platform.case_manager.models import (CaseFinanceModel,
                                                           CaseModel,
                                                           ClientModel)


class Command(BaseCommand):
    help = 'Crea el grupo del gestor de procesos y le asigna sus permisos.'

    @transaction.atomic
    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name=GESTOR_GROUP)

        # Ver, anadir y cambiar. **Borrar no**: no hay papelera --esta fuera
        # del alcance contratado-- y un cliente borrado se lleva por delante
        # sus casos y su historial financiero. Para dar de baja esta la
        # vigencia.
        wanted = []
        for model in (ClientModel, CaseModel, CaseFinanceModel):
            name = model._meta.model_name
            wanted += [f'view_{name}', f'add_{name}', f'change_{name}']

        permissions = Permission.objects.filter(
            codename__in=wanted,
            content_type__app_label='case_manager',
        )
        group.permissions.add(*permissions)

        verb = 'Creado' if created else 'Actualizado'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} el grupo "{GESTOR_GROUP}" con {permissions.count()} '
            f'permisos. Sus miembros necesitan ademas `is_staff` para entrar '
            f'al admin.'
        ))

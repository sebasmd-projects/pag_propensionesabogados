"""
Trae a la base los expedientes que estaban en `localStorage.propDemo`.

Por que hace falta
------------------
Lo que el despacho lleva cargado hasta hoy no esta en ningun servidor: esta en
`localStorage` del navegador donde se escribio. No se puede leer desde aqui, y
si ese navegador borra su cache, se pierde. Asi que la migracion no la puede
hacer el servidor solo: alguien tiene que exportar el JSON desde ese navegador
y pasarlo por este comando.

Como sacar el fichero
---------------------
En el navegador donde esta el panel, con la consola abierta (F12) en
`propensionesabogados.com`:

    copy(localStorage.getItem('propDemo'))

...y pegarlo en un fichero. Luego:

    manage.py import_propdemo propdemo.json

Se puede ensayar antes sin escribir nada:

    manage.py import_propdemo propdemo.json --dry-run

El formato de origen
--------------------
Un objeto cuya clave es la cedula y cuyo valor son las claves de dos letras
que usaba el JavaScript::

    {"16484186": {"n": "Carlos ...", "s": "Representación judicial",
                  "e": 2, "v": "activo", "mm": "Modalidad de pago",
                  "hp": 6000000, "ge": 2000000, ...}}

Cada una de esas letras se traduce abajo, en `FIELD_MAP`, que es el unico
sitio donde hace falta volver a mirar si aparece un fichero mas viejo con
claves que ya no existen.
"""

import json
from pathlib import Path
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.project.api.platform.case_manager import choices
from apps.project.api.platform.case_manager.models import (CaseFinanceModel,
                                                           CaseModel,
                                                           ClientModel)

#: Clave del JSON -> campo de `CaseModel`. Las que no estan aqui (`n`, `v`)
#: son del cliente, y las de dinero van en `CaseFinanceModel`.
FIELD_MAP = {
    's': 'service',
    't': 'procedure',
    'a': 'area',
    'st': 'subtype',
    'st2': 'second_subtype',
    'i': 'instance',
    'r': 'case_number',
    'd': 'court',
    'cp': 'city',
    'sec': 'sector',
    'ent': 'entity',
    'ra': 'administrative_case_number',
    'ca': 'administrative_city',
    'ip': 'police_instance',
    'insp': 'police_office',
    'rp': 'police_case_number',
    'cpol': 'police_city',
}

#: Longitud maxima de cada campo de texto, para recortar en vez de reventar.
MAX_LENGTHS = {
    field.name: field.max_length
    for field in CaseModel._meta.get_fields()
    if getattr(field, 'max_length', None)
}


class Command(BaseCommand):
    help = (
        'Importa a la base los expedientes exportados de `localStorage.propDemo`.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            type=Path,
            help='Fichero JSON exportado del navegador.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Dice que haria y no escribe nada.',
        )

    def handle(self, *args, **options):
        path = options['path']
        dry_run = options['dry_run']

        if not path.exists():
            raise CommandError(f'No existe el fichero {path}.')

        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as error:
            raise CommandError(f'El fichero no es JSON valido: {error}')

        if not isinstance(data, dict):
            raise CommandError(
                'Se esperaba un objeto cuyas claves sean las cedulas.'
            )

        created, updated, skipped = 0, 0, 0

        # Todo o nada: una importacion a medias deja al despacho sin saber
        # que entro y que no, que es peor que no haber empezado.
        with transaction.atomic():
            for identification, record in data.items():
                digits = ''.join(c for c in str(identification) if c.isdigit())
                name = (record.get('n') or '').strip()

                if not digits or not name:
                    self.stderr.write(
                        f'  se omite "{identification}": sin cedula o sin nombre'
                    )
                    skipped += 1
                    continue

                was_created = self._import_one(digits, name, record)
                created += was_created
                updated += not was_created

            if dry_run:
                transaction.set_rollback(True)

        summary = (
            f'{created} clientes nuevos, {updated} actualizados, '
            f'{skipped} omitidos.'
        )
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'Ensayo (no se escribio nada): {summary}'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(summary))

    def _import_one(self, identification: str, name: str, record: dict) -> bool:
        client, created = ClientModel.objects.update_or_create(
            identification=identification,
            defaults={
                'full_name': name,
                # `v` era "activo" / "inactivo"; cualquier otra cosa se trata
                # como vigente, que es el valor por defecto de la pantalla.
                'is_active': (record.get('v') or 'activo') == 'activo',
            },
        )

        fields = {}
        for key, field in FIELD_MAP.items():
            value = record.get(key)
            if value in (None, ''):
                continue
            value = str(value).strip()
            limit = MAX_LENGTHS.get(field)
            fields[field] = value[:limit] if limit else value

        # `e` era el indice dentro del array de etapas. Si viene fuera de
        # rango se deja en la primera, que es lo unico seguro: inventar una
        # etapa mas avanzada le diria al cliente que su caso va por donde no
        # va.
        stage = record.get('e')
        valid_stages = {value for value, _label in choices.Stage.choices}
        fields['stage'] = (
            int(stage) if isinstance(stage, int) and stage in valid_stages
            else choices.Stage.DOCUMENTS_RECEIVED
        )

        case, _ = CaseModel.objects.update_or_create(
            client=client, defaults=fields
        )

        self._import_finance(case, record)
        return created

    def _import_finance(self, case: CaseModel, record: dict) -> None:
        mandate = record.get('mm')
        if not mandate:
            return

        valid = {value for value, _label in choices.Mandate.choices}
        if mandate not in valid:
            self.stderr.write(
                f'  {case.client.identification}: modalidad desconocida '
                f'"{mandate}", no se importa el dinero'
            )
            return

        defaults = {
            'mandate': mandate,
            # `me` era "si" / "no".
            'show_in_dashboard': (record.get('me') or 'si') == 'si',
        }

        # fi tiene precision mensual: se representa con el primer dia del mes.
        if record.get('fi'):
            try:
                raw_date = str(record['fi'])
                defaults['start_date'] = date.fromisoformat(raw_date + '-01' if len(raw_date) == 7 else raw_date)
            except ValueError:
                self.stderr.write(f'  {case.client.identification}: fecha de inicio inválida')

        if mandate == choices.Mandate.CONTINGENCY:
            defaults['contingency_percentage'] = _as_int(record.get('pl'))
            defaults['contingency_value'] = _as_int(record.get('vl'))
            if defaults['contingency_percentage'] == 0:
                defaults['paid_amount'] = _as_int(record.get('pr'))
                if record.get('estadoPagoV29') == 'PAGADO':
                    defaults['paid_amount'] = max(defaults['paid_amount'], defaults['contingency_value'])
        elif mandate == choices.Mandate.PAYMENT:
            defaults['agreed_fee'] = _as_int(record.get('hp'))
            defaults['paid_amount'] = _as_int(record.get('ge'))

        CaseFinanceModel.objects.update_or_create(case=case, defaults=defaults)


def _as_int(value) -> int:
    """
    Un importe del JSON como entero no negativo.

    El navegador guardaba lo que hubiera en el campo: cadenas, vacios y algun
    `null`. Un importe que no se entiende se trata como cero y no como un
    fallo, porque parar la importacion entera por un campo mal escrito dejaria
    fuera a todos los demas.
    """
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return 0

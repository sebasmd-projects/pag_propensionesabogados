"""Regresiones del formato st/st2 exportado y de los selectores del gestor."""
import json
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.forms.models import model_to_dict
from django.test import TestCase

from ..choices import Service
from ..forms import CaseForm
from ..models import CaseFinanceModel, CaseModel, ClientModel


class ClassificationTests(TestCase):
    def test_imported_judicial_cases_can_be_edited(self):
        records = {
            '10001': {'n': 'Cliente pensional', 's': Service.JUDICIAL,
                      'a': 'Pensional / Seguridad Social', 't': '', 'st': 'Laboral',
                      'st2': 'Pensión de vejez', 'e': 3, 'i': 'Primera instancia',
                      'r': '63001310500120230010200', 'd': 'Juzgado del Circuito',
                      'cp': 'Armenia', 'fi': '2024-02', 'mm': 'Cuota litis',
                      'pl': 0, 'vl': 15000000, 'pr': 15000000, 'estadoPagoV29': 'PAGADO'},
            '10002': {'n': 'Cliente consumidor', 's': Service.JUDICIAL,
                      'st': 'Superintendencias', 'st2': 'Protección al consumidor',
                      'e': 3, 'i': 'Primera instancia', 'r': '26-277458-9',
                      'd': 'Superintendencia', 'cp': 'Bogota', 'fi': '2026-03',
                      'mm': 'Cuota litis', 'pl': 20, 'vl': 13000000},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cases.json'
            path.write_text(json.dumps(records))
            call_command('import_propdemo', str(path), stdout=StringIO())
        for case in CaseModel.objects.all():
            with self.subTest(subtype=case.subtype):
                case.full_clean()
                form = CaseForm(data=model_to_dict(case), instance=case)
                self.assertTrue(form.is_valid(), form.errors)
                for name in ('subtype', 'second_subtype', 'instance'):
                    self.assertIsInstance(form.fields[name].widget, forms.Select)
                form.save()
                case.refresh_from_db()
                self.assertEqual(case.second_subtype, records[case.client.identification]['st2'])
        fixed = CaseFinanceModel.objects.get(contingency_percentage=0)
        fixed.full_clean()
        self.assertEqual(fixed.start_date, date(2024, 2, 1))
        self.assertEqual(fixed.paid, 15000000)
        self.assertEqual(fixed.balance, 0)
        self.assertFalse(CaseFinanceModel.objects.debtors().exists())
        totals = CaseFinanceModel.objects.totals()
        self.assertEqual(totals['balance'], 0)
        self.assertEqual(totals['paid'], 15000000)
        self.assertEqual(totals['expectation'], 13000000)

    def setUp(self):
        self.customer = ClientModel.objects.create(identification='20000', full_name='Cliente')

    def data(self, **kwargs):
        return {'client': self.customer.pk, 'service': Service.JUDICIAL,
                'stage': 0, **kwargs}

    def test_dependent_options_use_posted_parents(self):
        form = CaseForm(data=self.data(subtype='Superintendencias', second_subtype='Protección al consumidor'))
        self.assertTrue(form.is_valid(), form.errors)
        bad = CaseForm(data=self.data(subtype='Laboral', second_subtype='Protección al consumidor'))
        self.assertFalse(bad.is_valid())
        self.assertIn('second_subtype', bad.errors)

    def test_server_rejects_forged_subtype(self):
        form = CaseForm(data=self.data(area='Civil', subtype='<inventado>'))
        self.assertFalse(form.is_valid())
        self.assertIn('subtype', form.errors)

    def test_other_requires_description_and_round_trips(self):
        for name in ('service', 'procedure', 'area', 'subtype', 'second_subtype'):
            with self.subTest(field=name):
                data = self.data(**{name: 'Otro'})
                form = CaseForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn(name + '_other', form.errors)
                data[name + '_other'] = 'Especialidad particular'
                form = CaseForm(data=data)
                self.assertTrue(form.is_valid(), form.errors)
                case = form.save()
                case.refresh_from_db()
                self.assertEqual(getattr(case, name + '_display'), 'Especialidad particular')

    def test_direct_area_subtype_remains_valid(self):
        form = CaseForm(data=self.data(area='Civil', subtype='Responsabilidad civil'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_model_rejects_wrong_second_level(self):
        case = CaseModel(client=self.customer, service=Service.JUDICIAL,
                         subtype='Laboral', second_subtype='Protección al consumidor')
        with self.assertRaises(ValidationError):
            case.full_clean()

    def test_legacy_free_second_level_is_preserved_but_not_forgeable(self):
        case = CaseModel.objects.create(
            client=self.customer, service=Service.JUDICIAL, area='Civil',
            subtype='Responsabilidad civil', second_subtype='Detalle histórico',
        )
        data = model_to_dict(case)
        form = CaseForm(data=data, instance=case)
        self.assertTrue(form.is_valid(), form.errors)
        data['second_subtype'] = 'Texto ajeno al catálogo'
        self.assertFalse(CaseForm(data=data, instance=case).is_valid())

    def test_partial_fixed_payment_matches_aggregates(self):
        case = CaseModel.objects.create(client=self.customer, service=Service.JUDICIAL)
        finance = CaseFinanceModel.objects.create(
            case=case, mandate='Cuota litis', contingency_percentage=0,
            contingency_value=1000000, paid_amount=250000,
        )
        finance.full_clean()
        self.assertEqual(finance.balance, 750000)
        self.assertTrue(CaseFinanceModel.objects.debtors().filter(pk=finance.pk).exists())
        self.assertEqual(CaseFinanceModel.objects.totals()['balance'], finance.balance)
        finance.contingency_percentage = 20
        with self.assertRaises(ValidationError) as error:
            finance.full_clean()
        self.assertIn('paid_amount', error.exception.message_dict)

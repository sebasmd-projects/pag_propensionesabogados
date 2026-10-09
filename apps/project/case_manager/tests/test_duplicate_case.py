"""El aviso se valida en servidor y permite confirmar sin perder los datos."""
from django.forms.models import model_to_dict
from django.test import TestCase
from django.urls import reverse
from ..choices import Service
from ..forms import CaseForm
from ..models import CaseModel, ClientModel
from .test_access import login_as, make_user


class DuplicateCaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.person = ClientModel.objects.create(identification='778899', full_name='Duplicados')
        cls.other = ClientModel.objects.create(identification='778898', full_name='Otro cliente')
        cls.case = CaseModel.objects.create(client=cls.person, service=Service.JUDICIAL, case_number='ab-12 34')
        cls.actor = make_user('duplicates', gestor=True)

    def data(self, **kwargs):
        return {'client': self.person.pk, 'service': Service.JUDICIAL, 'stage': 0,
                'case_number': ' AB1234 ', **kwargs}

    def test_normalized_reference_warns_and_links_existing(self):
        form = CaseForm(self.data())
        self.assertFalse(form.is_valid())
        self.assertEqual(form.duplicate_case, self.case)
        self.assertIn('radicado', str(form.non_field_errors()))
        login_as(self.client, self.actor.username)
        response = self.client.post(reverse('case_manager:gestor_case_create'), self.data())
        self.assertContains(response, reverse('case_manager:gestor_case_update', args=[self.case.pk]))
        self.assertContains(response, 'Continuar y guardar')
        self.assertContains(response, 'name="confirm_duplicate"')
        self.assertEqual(CaseModel.objects.count(), 1)

    def test_without_reference_warns_without_radicado_text(self):
        form = CaseForm(self.data(case_number=''))
        self.assertFalse(form.is_valid())
        self.assertNotIn('radicado', str(form.non_field_errors()))

    def test_different_client_service_reference_or_subtype_does_not_warn(self):
        for changes in [{'client': self.other.pk}, {'service': Service.ADMINISTRATIVE},
                        {'case_number': 'AB1235'}, {'subtype': 'Laboral'}]:
            with self.subTest(changes=changes):
                form = CaseForm(self.data(**changes))
                self.assertTrue(form.is_valid(), form.errors)
                self.assertIsNone(form.duplicate_case)

    def test_deleted_case_does_not_warn(self):
        self.case.soft_delete(self.actor)
        form = CaseForm(self.data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_confirm_saves_through_view(self):
        login_as(self.client, self.actor.username)
        data = self.data(confirm_duplicate='1', **{'finance-TOTAL_FORMS': '0',
            'finance-INITIAL_FORMS': '0', 'finance-MIN_NUM_FORMS': '0', 'finance-MAX_NUM_FORMS': '1'})
        response = self.client.post(reverse('case_manager:gestor_case_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CaseModel.objects.count(), 2)

    def test_edit_reference_or_service_warns_but_unrelated_edit_does_not(self):
        edited = CaseModel.objects.create(client=self.person, service=Service.ADMINISTRATIVE, case_number='AB1234')
        form = CaseForm(self.data(), instance=edited)
        self.assertFalse(form.is_valid())
        edited.refresh_from_db()
        edited.service = Service.JUDICIAL
        edited.case_number = 'other'
        edited.save()
        form = CaseForm(self.data(), instance=edited)
        self.assertFalse(form.is_valid())
        edited.refresh_from_db()
        edited.case_number = self.case.case_number
        edited.save()
        data = model_to_dict(edited)
        data['stage'] = 1
        form = CaseForm(data, instance=edited)
        self.assertTrue(form.is_valid(), form.errors)

    def test_legacy_reference_fields_are_compared(self):
        self.case.case_number = ''
        self.case.administrative_case_number = 'AB-1234'
        self.case.save()
        form = CaseForm(self.data())
        self.assertFalse(form.is_valid())
        self.assertEqual(form.duplicate_case, self.case)

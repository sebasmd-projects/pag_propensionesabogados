"""Contrato del flujo final ARBOL41 / ETAPAS_V35 del HTML del cliente."""
import json
from pathlib import Path

from django.test import TestCase

from .. import choices
from ..forms import CaseForm
from ..models import CaseModel, ClientModel

REFERENCE = json.loads((Path(__file__).parent / 'fixtures/reference_flow.json').read_text())


class DynamicFlowTests(TestCase):
    def setUp(self):
        self.customer = ClientModel.objects.create(identification='555123', full_name='Prueba flujo')

    def test_every_reference_branch_can_be_selected_and_saved(self):
        for service, branches in REFERENCE['services'].items():
            self.assertEqual(set(choices.subtypes_for(service)) - {'Otro'}, set(branches))
            self.assertEqual(list(choices.instances_for(service)), REFERENCE['instances'][service])
            for parent, children in branches.items():
                self.assertEqual(set(choices.second_subtypes_for(service, parent)) - {'Otro'}, set(children))
                for process in children or ['']:
                    with self.subTest(service=service, parent=parent, process=process):
                        form = CaseForm(data={'client': self.customer.pk, 'service': service,
                                              'subtype': parent, 'second_subtype': process, 'stage': 0})
                        self.assertTrue(form.is_valid(), form.errors)
                        saved = form.save()
                        opened = CaseForm(instance=saved)
                        self.assertEqual(opened['subtype'].value(), parent)
                        self.assertEqual(opened['second_subtype'].value() or '', process)
                        self.assertEqual(opened.fields['second_subtype'].flow_hidden, not bool(children))

    def test_initial_html_only_exposes_applicable_fields(self):
        empty = CaseForm()
        for name in ('subtype', 'second_subtype', 'instance', 'court'):
            self.assertTrue(empty.fields[name].flow_hidden, name)
        for service in choices.Service.values:
            form = CaseForm(initial={'service': service})
            self.assertEqual(form.fields['subtype'].flow_hidden, service == choices.Service.OTHER)
            self.assertTrue(form.fields['second_subtype'].flow_hidden)
            self.assertEqual(form.fields['court'].flow_hidden, service != choices.Service.JUDICIAL)

    def test_legacy_process_restores_ancestors_and_round_trips(self):
        for service, subtype, process in (
            (choices.Service.JUDICIAL, 'Administrativo', 'Nulidad y restablecimiento del derecho'),
            (choices.Service.ADMINISTRATIVE, 'Nulidad y restablecimiento del derecho', ''),
            (choices.Service.JUDICIAL, '', 'Nulidad y restablecimiento del derecho'),
        ):
            with self.subTest(service=service, subtype=subtype):
                case = CaseModel.objects.create(client=self.customer, service=service,
                                               subtype=subtype, second_subtype=process)
                opened = CaseForm(instance=case)
                self.assertEqual(opened['service'].value(), choices.Service.JUDICIAL)
                self.assertEqual(opened['subtype'].value(), 'Contencioso administrativo')
                self.assertEqual(opened['second_subtype'].value(), 'Nulidad y restablecimiento del derecho')
                # Abrir no modifica la base de datos; la reclasificacion se guarda al confirmar.
                case.refresh_from_db()
                self.assertEqual(case.subtype, subtype)
                submitted = CaseForm(data=opened.initial, instance=case)
                self.assertTrue(submitted.is_valid(), submitted.errors)
                submitted.save()
                case.refresh_from_db()
                self.assertEqual(case.subtype, 'Contencioso administrativo')

    def test_free_text_and_valid_branches_are_not_reclassified(self):
        for triple in [('Otro', 'Otro', 'Personalizado'),
                       ('Administrativo', 'Acción de tutela', ''),
                       ('Representación judicial', 'Laboral', 'Pensión de vejez')]:
            self.assertEqual(choices.restore_classification(*triple), tuple(triple))

    def test_an_instance_from_previous_service_is_not_offered(self):
        case = CaseModel.objects.create(client=self.customer, service=choices.Service.JUDICIAL,
                                       instance='Casación')
        form = CaseForm(data={'client': self.customer.pk, 'service': choices.Service.CONSULTING,
                              'instance': 'Casación', 'stage': 0}, instance=case)
        self.assertFalse(form.is_valid())
        self.assertIn('instance', form.errors)

    def test_legacy_details_are_available_without_procedure(self):
        case = CaseModel.objects.create(client=self.customer, service=choices.Service.ADMINISTRATIVE,
                                       entity='Entidad registrada', police_office='Autoridad registrada')
        form = CaseForm(instance=case)
        self.assertTrue(form.show_administrative)
        self.assertTrue(form.show_police)

    def test_rendered_create_and_edit_pages(self):
        import os
        from django.urls import reverse
        from .test_access import make_user
        self.client.force_login(make_user('flow-tester', gestor=True))
        case = CaseModel.objects.create(
            client=self.customer, service=choices.Service.JUDICIAL, subtype='Administrativo',
            second_subtype='Nulidad y restablecimiento del derecho', instance='Primera instancia',
        )
        pages = {
            'create': reverse('case_manager:gestor_case_create'),
            'edit': reverse('case_manager:gestor_case_update', args=[case.pk]),
        }
        for name, url in pages.items():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'case-classification')
            if name == 'edit':
                self.assertContains(response, 'value="Contencioso administrativo" selected')
                self.assertContains(response, 'value="Nulidad y restablecimiento del derecho" selected')
            # Exportación opcional de HTML sintético para la prueba DOM de los scripts reales.
            directory = os.environ.get('CASE_FLOW_HTML_DIR')
            if directory:
                path = Path(directory)
                path.mkdir(parents=True, exist_ok=True)
                (path / (name + '.html')).write_bytes(response.content)

    def test_distribution_uses_the_selected_judicial_area(self):
        from ..models import CaseFinanceModel
        case = CaseModel.objects.create(
            client=self.customer, service=choices.Service.JUDICIAL,
            area='Administrativo', subtype='Contencioso administrativo',
            second_subtype='Nulidad y restablecimiento del derecho',
        )
        CaseFinanceModel.objects.create(case=case, mandate=choices.Mandate.PAYMENT, agreed_fee=100)
        self.assertEqual(CaseFinanceModel.objects.by_area(), [
            {'area': 'Contencioso administrativo', 'total': 100, 'share': 100},
        ])

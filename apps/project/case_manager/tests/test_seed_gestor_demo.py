"""El comando `seed_gestor_demo`: cubre lo que promete y no duplica."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from ..access import can_use_case_manager
from ..choices import Mandate, Stage
from ..models import (CaseFinanceModel, CaseModel, CaseNoteModel,
                      ClientModel)


def seed(*args):
    call_command('seed_gestor_demo', *args, stdout=StringIO())


class SeedGestorDemoTests(TestCase):
    def test_creates_valid_data_without_duplicating(self):
        seed()
        counts = (ClientModel.objects.count(), CaseModel.objects.count(),
                  CaseFinanceModel.objects.count(), CaseNoteModel.objects.count())

        self.assertGreaterEqual(counts[0], 15)
        seed()
        self.assertEqual(counts, (
            ClientModel.objects.count(), CaseModel.objects.count(),
            CaseFinanceModel.objects.count(), CaseNoteModel.objects.count()))

    def test_everything_validates_and_amounts_are_at_least_a_million(self):
        seed()
        for client in ClientModel.objects.all():
            client.full_clean()
        for case in CaseModel.objects.all():
            case.full_clean()
        for note in CaseNoteModel.objects.all():
            note.full_clean()

        for finance in CaseFinanceModel.objects.all():
            finance.full_clean()
            amounts = [finance.agreed_fee, finance.paid_amount,
                       finance.contingency_value,
                       *(row['amount'] for row in finance.payment_history)]
            for amount in amounts:
                self.assertTrue(amount == 0 or amount >= 1_000_000, amount)

    def test_covers_the_main_scenarios(self):
        seed()
        finances = CaseFinanceModel.objects
        self.assertEqual(
            {m for m in Mandate.values},
            set(finances.values_list('mandate', flat=True)))
        self.assertEqual(
            set(Stage.values), set(CaseModel.objects.values_list('stage', flat=True)))
        self.assertTrue(finances.debtors().exists())
        self.assertTrue(finances.expectations().exists())
        self.assertTrue(CaseModel.objects.filter(paz_y_salvo_authorized=True).exists())
        self.assertTrue(ClientModel.objects.filter(is_active=False).exists())
        self.assertTrue(finances.filter(show_in_dashboard=False).exists())

    def test_user_option_grants_the_gestor_group_only(self):
        user = get_user_model().objects.create_user(
            username='demo_gestor', password='una-contrasena-larga-de-verdad')
        hashed = user.password

        seed('--user', 'demo_gestor')
        user.refresh_from_db()

        self.assertTrue(can_use_case_manager(user))
        self.assertEqual(user.password, hashed)

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from ..models import CaseModel, ClientModel
from .test_access import make_user
from .test_public_access import identificarse


class AuthenticatedPortalTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('case_manager:public_query')
        self.record = ClientModel.objects.create(
            identification='16484186', full_name='Cliente', email='client@example.test',
        )
        self.case = CaseModel.objects.create(client=self.record, service='Representación judicial')

    def test_manager_enters_without_sending_otp_and_can_reload(self):
        user = make_user('manager', gestor=True)
        self.client.force_login(user)
        response = self.client.post(self.url, {'identification': self.record.identification})
        self.assertEqual(list(response.context['cases']), [self.case])
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(list(self.client.get(self.url).context['cases']), [self.case])

    def test_account_without_group_can_consult_any_client_without_otp(self):
        self.client.force_login(make_user('ordinary'))
        for identification in ('16484186', '999'):
            if identification == '999':
                other = ClientModel.objects.create(identification='999', full_name='Otro')
                CaseModel.objects.create(client=other, service='Representación judicial')
            response = self.client.post(self.url, {'identification': identification})
            self.assertEqual(response.context['client'].identification, identification)
            self.assertNotIn('code_form', response.context)
        self.assertEqual(len(mail.outbox), 0)

    def test_verified_client_can_reload_and_query_same_client_without_otp(self):
        identificarse(self.client)
        sent = len(mail.outbox)
        self.assertEqual(list(self.client.get(self.url).context['cases']), [self.case])
        response = self.client.post(self.url, {'identification': self.record.identification})
        self.assertEqual(list(response.context['cases']), [self.case])
        self.assertEqual(len(mail.outbox), sent)
        other = ClientModel.objects.create(identification='999', full_name='Otro', email='other@example.test')
        response = self.client.post(self.url, {'identification': other.identification})
        self.assertNotIn('cases', response.context)
        self.assertIn('code_form', response.context)

    def test_account_access_expires_on_logout(self):
        user = make_user('manager', gestor=True)
        self.client.force_login(user)
        self.client.post(self.url, {'identification': self.record.identification})
        self.client.logout()
        self.assertNotIn('cases', self.client.get(self.url).context)

    def test_reloading_checks_current_client_status(self):
        identificarse(self.client)
        self.record.is_active = False
        self.record.save()
        response = self.client.get(self.url)
        self.assertTrue(response.context['inactive'])
        self.assertNotIn('cases', response.context)

    def test_authenticated_account_can_finish_pending_query_without_code(self):
        self.client.post(self.url, {'identification': self.record.identification})
        sent = len(mail.outbox)
        self.client.force_login(make_user('ordinary'))
        response = self.client.post(self.url, {'resend': '1'})
        self.assertEqual(list(response.context['cases']), [self.case])
        self.assertEqual(len(mail.outbox), sent)

    def test_account_can_open_authorized_settlement_letter(self):
        self.case.paz_y_salvo_authorized = True
        self.case.save()
        self.client.force_login(make_user('ordinary'))
        self.client.post(self.url, {'identification': self.record.identification})
        url = reverse('case_manager:paz_y_salvo', args=[self.case.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_eye_link_opens_requested_client_instead_of_previous_client(self):
        self.client.force_login(make_user('manager', gestor=True))
        self.client.post(self.url, {'identification': self.record.identification})
        other = ClientModel.objects.create(identification='999', full_name='Otro')
        other_case = CaseModel.objects.create(client=other, service='Representación judicial')
        response = self.client.get(self.url, {'identification': '999'})
        self.assertEqual(list(response.context['cases']), [other_case])
        self.assertEqual(response.context['client'], other)
        self.assertEqual(len(mail.outbox), 0)
        listing = self.client.get(reverse('case_manager:gestor_client_list'))
        self.assertContains(listing, self.url + '?identification=999')
        self.assertContains(listing, 'bi bi-eye')
        invalid = self.client.get(self.url, {'identification': '000'})
        self.assertEqual(invalid.status_code, 400)
        self.assertNotIn('cases', invalid.context)

    def test_eye_url_does_not_authorize_anonymous_visitor(self):
        response = self.client.get(self.url, {'identification': self.record.identification})
        self.assertNotIn('cases', response.context)
        self.assertEqual(len(mail.outbox), 0)

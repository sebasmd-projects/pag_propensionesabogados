import logging

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.views.generic.detail import DetailView
from honeypot.decorators import check_honeypot

from .forms import ContactForm
from .models import ContactModel, ModalBannerModel, TeamMemberModel

logger = logging.getLogger(__name__)


@method_decorator(check_honeypot, name='post')
class IndexTemplateView(FormView):
    template_name = "pages/index.html"
    form_class = ContactForm
    success_url = reverse_lazy('core:index')

    def form_valid(self, form):
        unique_id = form.cleaned_data.get('unique_id')
        honeypot_field = form.cleaned_data.get('email_confirm')

        if ContactModel.objects.filter(unique_id=unique_id).exists():
            form.add_error(None, _("This form has already been sent."))
            return self.form_invalid(form)

        if honeypot_field:
            form.save()
            return render(self.request, self.template_name, {'form': None, 'success_message': True})

        contact = form.save()
        user_language = self.request.LANGUAGE_CODE

        html_message = render_to_string('email/contact_email_template.html', {
            'names': contact.name,
            'LANGUAGE_CODE': user_language,
        })

        subject = _('Message Received! | PROPENSIONES ABOGADOS')
        plain_message = _('Thank you %(name)s for contacting us.') % {
            'name': contact.name}

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[contact.email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred sending mail: {e}")
            return render(self.request, self.template_name, {'form': None, 'success_message': True})

        return render(self.request, self.template_name, {'form': None, 'success_message': True})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        banner = ModalBannerModel.objects.filter(is_active=True).first()
        team_members = TeamMemberModel.objects.filter(
            is_active=True).order_by("display_order", "full_name")

        context['modal_banner'] = banner
        context['team_members'] = team_members

        return context


class TeamMemberDetailView(DetailView):
    model = TeamMemberModel
    template_name = "pages/team_detail.html"
    context_object_name = "member"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return TeamMemberModel.objects.filter(is_active=True)


class TermsAndConditionsView(TemplateView):
    template_name = "pages/terms_and_conditions.html"


class PrivacyPolicyView(TemplateView):
    template_name = "pages/privacy_policy.html"


class DocumentsView(TemplateView):
    template_name = "pages/documents.html"


def security_txt_view(request):
    content = (
        "Contact: mailto:info@propensionesabogados.com\n"
        "Expires: 2030-12-31T05:00:00.000Z\n"
        "Canonical: https://propensionesabogados.com/.well-known/security.txt\n"
    )
    return HttpResponse(content, content_type='text/plain')

import logging

from django.conf import settings
from django.core.cache import caches
from django.core.mail import get_connection, send_mail
from django.db import DatabaseError, connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import TemplateView, RedirectView
from django.views.generic.edit import FormView
from django.views.generic.detail import DetailView
from apps.common.utils.honeypot import check_honeypot

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
            return render(
                self.request,
                self.template_name,
                {'form': None, 'success_message': True}
            )

        contact = form.save()
        user_language = self.request.LANGUAGE_CODE

        html_message = render_to_string(
            'email/contact_email_template.html',
            {
                'names': contact.name,
                'LANGUAGE_CODE': user_language,
            }
        )

        subject = _('Message Received! | PROPENSIONES ABOGADOS')
        plain_message = _('Thank you %(name)s for contacting us.') % {
            'name': contact.name
        }

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

        return render(
            self.request,
            self.template_name,
            {'form': None, 'success_message': True}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        banner = ModalBannerModel.objects.filter(is_active=True).first()
        team_members = TeamMemberModel.objects.filter(
            is_active=True
        ).order_by("display_order", "full_name")

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


class CalendarView(RedirectView):
    url = "https://calendly.com/enlace-juvl/centro-de-conciliacion"
    permanent = False


def security_txt_view(request):
    content = (
        "Contact: mailto:info@propensionesabogados.com\n"
        "Expires: 2030-12-31T05:00:00.000Z\n"
        "Canonical: https://propensionesabogados.com/.well-known/security.txt\n"
    )
    return HttpResponse(content, content_type='text/plain')


class HealthCheckView(View):
    """
    Salud de la aplicacion, para el monitor y para `manage.py check_health`.

    Publica a proposito y **sin datos**: solo dice si responden la base de
    datos, la cache y el servidor de correo, con el nombre de la excepcion
    cuando algo falla (nunca su mensaje, que puede llevar hosts o usuarios).

    Respuesta JSON:
    {"response": "OK" | "Error" | "Other Error", "status": <codigo>,
     "checks": {"database": {"ok": bool, "detail": str}, "cache": ..., "email": ...}}
    """

    def get(self, request, *args, **kwargs):
        try:
            checks = {
                'database': self._check_database(),
                'cache': self._check_cache(),
                'email': self._check_email(),
            }

            if all(item.get('ok', False) for item in checks.values()):
                response_text, status_code = 'OK', 200
            else:
                response_text, status_code = 'Error', 503

            return JsonResponse({
                'response': response_text,
                'status': status_code,
                'checks': checks,
            }, status=status_code)
        except Exception:  # noqa: BLE001
            logger.exception('HealthCheckView - unhandled exception')
            return JsonResponse(
                {'response': 'Other Error', 'status': 500, 'checks': {}},
                status=500,
            )

    def _check_database(self):
        """Que la conexion a la base de datos funcione."""
        try:
            connection.ensure_connection()

            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()

            return {'ok': True, 'detail': 'Database OK'}
        except DatabaseError as error:
            logger.warning('HealthCheck - database error: %s', error)
            return {'ok': False,
                    'detail': f'Database error: {error.__class__.__name__}'}
        except Exception as error:  # noqa: BLE001
            logger.exception('HealthCheck - unexpected DB error')
            return {'ok': False,
                    'detail': f'Unexpected DB error: {error.__class__.__name__}'}

    def _check_cache(self):
        """Que la cache por defecto escriba y relea."""
        try:
            cache = caches['default']
            cache.set('health_check_test_key', 'ok', timeout=10)

            if cache.get('health_check_test_key') == 'ok':
                return {'ok': True, 'detail': 'Cache OK'}

            return {'ok': False, 'detail': 'Cache set/get failed'}
        except Exception as error:  # noqa: BLE001
            logger.warning('HealthCheck - cache error: %s', error)
            return {'ok': False,
                    'detail': f'Cache error: {error.__class__.__name__}'}

    def _check_email(self):
        """
        Que el backend de correo se pueda abrir. No envia nada: abre y cierra
        la conexion.
        """
        try:
            mail_connection = get_connection()
            mail_connection.open()
            mail_connection.close()

            return {'ok': True, 'detail': 'Email backend OK'}
        except Exception as error:  # noqa: BLE001
            logger.warning('HealthCheck - email error: %s', error)
            return {'ok': False,
                    'detail': f'Email error: {error.__class__.__name__}'}

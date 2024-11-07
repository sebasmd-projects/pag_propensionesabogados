
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from .forms import FormWithCaptcha

class IndexTemplateView(FormView):
    template_name = "pages/index.html"
    form_class = FormWithCaptcha

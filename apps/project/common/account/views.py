from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View
from django.views.generic.edit import FormView

from apps.project.common.users.models import UserModel

from .forms import UserRegisterForm

# El acceso vive en `login_view.PropensionesLoginView`, que es el asistente de
# `django-two-factor-auth` con la entrada por codigo al correo. Aqui estaba
# antes un `FormView` que llamaba a `authenticate()` sin la peticion, asi que
# `django-axes` no podia contar nada ni aplicar ningun bloqueo.


class UserLogoutView(View):
    def get(self, request, *args, **kwargs):
        from django.contrib.auth import logout

        logout(request)
        return HttpResponseRedirect(
            reverse(
                'account:login'
            )
        )


class UserRegisterView(FormView):
    template_name = "account/register.html"
    form_class = UserRegisterForm

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('core:index')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        UserModel.objects.create_user(
            username=form.cleaned_data['username'],
            email=form.cleaned_data['email'],
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
            password=form.cleaned_data['password'],
        )
        return super(UserRegisterView, self).form_valid(form)

    def form_invalid(self, form):
        return super(UserRegisterView, self).form_invalid(form)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        else:
            return reverse('core:index')

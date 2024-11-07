from django.views.generic import View
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.urls import reverse

class UserLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect(
            reverse(
                'index:home'
            )
        )
        

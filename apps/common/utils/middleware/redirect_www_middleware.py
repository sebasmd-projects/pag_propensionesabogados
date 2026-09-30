from django.http import HttpResponsePermanentRedirect


class RedirectWWWMiddleware:
    """Manda `www.dominio` a `dominio` con un 301, conservando ruta y esquema."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if host.startswith('www.'):
            non_www_host = host[4:]
            scheme = 'https' if request.is_secure() else 'http'
            non_www_url = f'{scheme}://{non_www_host}{request.get_full_path()}'
            return HttpResponsePermanentRedirect(non_www_url)
        return self.get_response(request)

from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse


class RedirectAuthenticatedUserMiddleware:
    """
    Quien ya tiene sesion no vuelve a ver el acceso ni el registro.

    En gea solo miraba `two_factor:login`. Aqui las rutas reales son
    `accounts/login/` (que se publica con dos nombres, `account:login` y
    `two_factor:login`) y `accounts/register/`. Va detras de la autenticacion:
    necesita `request.user`.

    Solo se considera con sesion a quien ya termino el asistente de acceso
    (contrasena o codigo, y segundo factor si lo tiene): la biblioteca no
    inicia sesion hasta el ultimo paso, asi que no hay riesgo de sacar a
    alguien a mitad del proceso.
    """

    ROUTE_NAMES = ('account:login', 'two_factor:login', 'account:register')

    def __init__(self, get_response):
        self.get_response = get_response
        self._paths = None

    def _guarded_paths(self):
        # Se resuelve en la primera peticion, no al arrancar: las URL aun
        # pueden no estar cargadas cuando se construye la cadena.
        if self._paths is None:
            paths = set()
            for name in self.ROUTE_NAMES:
                try:
                    paths.add(reverse(name))
                except NoReverseMatch:
                    continue
            self._paths = paths
        return self._paths

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user is not None
            and user.is_authenticated
            and request.path in self._guarded_paths()
        ):
            return redirect('core:index')
        return self.get_response(request)

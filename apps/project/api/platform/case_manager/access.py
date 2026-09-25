"""
Quien puede ver y tocar el gestor.

Esta en un modulo propio y no repartido por las vistas por la misma razon que
en el resto del proyecto: una regla de acceso escrita tres veces son tres
reglas, y la que se olvida de actualizar es por donde se entra.

Lo que sustituye
----------------
Hasta ahora el panel de administracion del gestor se abria asi, en el
navegador::

    const claveAdmin = localStorage.getItem("procrm_admin_password");
    if (u === "propensi" && p === claveAdmin) { ...mostrar el panel... }

...con la contrasena por defecto escrita en la propia plantilla. Eso no es una
puerta: el panel ya estaba descargado en el navegador y la comparacion la hacia
el visitante. Cualquiera con la consola abierta entraba, y cualquiera que
leyera el HTML tenia la contrasena.

Ahora la sesion la lleva Django, la contrasena vive cifrada con Argon2 en
`UserModel`, y el acceso se comprueba **en el servidor, antes de responder**.

Dos puertas, no una
-------------------
- `GestorRequiredMixin` --- para la gente del despacho. Hace falta sesion
  iniciada **y** pertenecer al grupo `GESTOR_GROUP` (o ser superusuario).
- El portal publico no usa mixin: las cuentas autenticadas del despacho
  consultan sin OTP ni comprobacion adicional de grupos. Los visitantes
  acreditan al cliente mediante `portal_otp.verify()`; esa autorizacion se
  conserva en su sesion.
"""

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404

#: Grupo cuyos miembros manejan el gestor. Se crea con
#: `manage.py setup_case_manager_group`.
GESTOR_GROUP = getattr(settings, 'CASE_MANAGER_GROUP', 'gestor')


def can_use_case_manager(user) -> bool:
    """
    Si `user` puede usar el gestor.

    Es una funcion y no solo un mixin porque la misma pregunta se hace desde
    sitios que no son vistas --una plantilla, el admin, una prueba-- y
    conviene que todos lean la misma linea.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=GESTOR_GROUP).exists()


class GestorRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Exige sesion iniciada y pertenencia al grupo del gestor.

    **Responde 404 y no 403 a quien ha iniciado sesion pero no tiene el
    grupo.** Un 403 confirma que en esa direccion hay algo; un 404 no dice
    nada. A quien no ha iniciado sesion se le manda al acceso, que es lo util:
    ahi el problema se arregla entrando.
    """

    def test_func(self) -> bool:
        return can_use_case_manager(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise Http404
        return super().handle_no_permission()

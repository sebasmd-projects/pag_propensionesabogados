"""
Entrar con el nombre de usuario **o** con el correo.

La pantalla de acceso siempre dijo «Usuario o Correo», y este backend es lo
que lo hace verdad: Django solo sabe buscar por `USERNAME_FIELD`.

Tres cosas que la version anterior no hacia, y las tres se notan solo cuando
ya es tarde
------------------------------------------------------------------------
1. **No miraba si la cuenta esta activa.** Comprobaba la contrasena y
   devolvia el usuario, sin pasar por `user_can_authenticate()`. Por el
   formulario de acceso no se colaba nadie --`AuthenticationForm` lo
   comprueba aparte--, pero cualquier otra llamada a `authenticate()` dejaba
   entrar a una cuenta desactivada. Desactivar a alguien que se va del
   despacho tiene que bastar.

2. **Reventaba si `username` llegaba vacio.** Django llama a **todos** los
   backends con los mismos argumentos, asi que una llamada con otra clave
   --`authenticate(request, email=..., password=...)`-- dejaba `username` en
   `None` y `'@' in None` levanta `TypeError`. Un 500 en el acceso.

3. **Contestaba mas rapido cuando la cuenta no existia.** Sin cuenta no se
   comprobaba ninguna contrasena, y comprobar una contrasena con Argon2 tarda
   lo suyo: la diferencia se mide y dice si un correo esta dado de alta. Se
   ejecuta el mismo trabajo en los dos casos, que es lo que hace `ModelBackend`
   desde siempre.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get(UserModel.USERNAME_FIELD)

        if not identifier or password is None:
            return None

        identifier = identifier.strip()
        lookup = (
            {'email__iexact': identifier}
            if '@' in identifier
            else {'username__iexact': identifier}
        )

        try:
            user = UserModel._default_manager.get(**lookup)
        except UserModel.DoesNotExist:
            # El mismo trabajo que si existiera, para que tardar lo mismo no
            # delate cuales estan dadas de alta.
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # El modelo no obliga a que el correo sea unico --lo unico que
            # exige es la pareja (usuario, correo)--, asi que dos cuentas
            # pueden compartirlo. Con dos candidatas no hay forma de saber
            # cual se pedia, y adivinar seria dejar entrar en la cuenta
            # equivocada: no se deja entrar en ninguna.
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

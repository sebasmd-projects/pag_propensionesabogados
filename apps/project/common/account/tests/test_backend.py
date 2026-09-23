"""
El backend que deja entrar con el usuario o con el correo.

Las tres pruebas que importan son las de lo que **no** debe pasar: que una
cuenta desactivada no entre, que un argumento inesperado no tumbe el acceso, y
que dos cuentas con el mismo correo no dejen entrar en una al azar.
"""

from django.contrib.auth import authenticate, get_user_model
from django.test import RequestFactory, TestCase, override_settings

User = get_user_model()

PASSWORD = 'una-contrasena-larga-de-verdad'

#: Sin el guardian de `axes` delante: aqui se prueba el backend del correo, y
#: `authenticate()` sin peticion es justo lo que aquel esta para impedir.
SOLO_MODELO = override_settings(AUTHENTICATION_BACKENDS=[
    'django.contrib.auth.backends.ModelBackend',
    'apps.common.utils.backend.EmailOrUsernameModelBackend',
])


@SOLO_MODELO
class EmailOrUsernameBackendTests(TestCase):

    def setUp(self):
        self.request = RequestFactory().post('/accounts/login/')
        self.user = User.objects.create_user(
            username='ana', email='Ana@Propensionesabogados.com',
            password=PASSWORD, first_name='Ana', last_name='Prueba',
        )

    def test_entra_con_el_usuario(self):
        self.assertEqual(
            authenticate(self.request, username='ana', password=PASSWORD),
            self.user,
        )

    def test_entra_con_el_correo_sin_importar_las_mayusculas(self):
        self.assertEqual(
            authenticate(
                self.request,
                username='ana@propensionesabogados.com',
                password=PASSWORD,
            ),
            self.user,
        )

    def test_una_cuenta_desactivada_no_entra(self):
        """
        Desactivar a quien se va del despacho tiene que bastar. La version
        anterior comprobaba la contrasena y devolvia el usuario sin mirar
        `is_active`: por el formulario no se colaba nadie --eso lo comprueba
        `AuthenticationForm` aparte-- pero cualquier otra llamada si.
        """
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

        self.assertIsNone(authenticate(
            self.request,
            username='ana@propensionesabogados.com',
            password=PASSWORD,
        ))

    def test_sin_identificador_no_revienta(self):
        """
        Django llama a **todos** los backends con los mismos argumentos, asi
        que una llamada con otra clave dejaba `username` en `None`, y
        `'@' in None` levanta `TypeError`: un 500 en la pantalla de acceso.
        """
        self.assertIsNone(
            authenticate(self.request, correo='ana', password=PASSWORD)
        )

    def test_dos_cuentas_con_el_mismo_correo_no_dejan_entrar_en_ninguna(self):
        """
        El modelo solo exige que sea unica la pareja (usuario, correo), asi
        que el correo puede repetirse. Con dos candidatas no hay forma de
        saber cual se pedia, y adivinar seria dejar entrar en la equivocada.
        """
        User.objects.create_user(
            username='ana2', email='Ana@Propensionesabogados.com',
            password=PASSWORD, first_name='Ana', last_name='Otra',
        )

        self.assertIsNone(authenticate(
            self.request,
            username='ana@propensionesabogados.com',
            password=PASSWORD,
        ))

    def test_una_contrasena_equivocada_no_entra(self):
        self.assertIsNone(authenticate(
            self.request, username='ana', password='la-que-no-es'
        ))

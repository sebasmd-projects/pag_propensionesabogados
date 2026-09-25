"""
Los nombres con los que se puede pedir el sitio.

Hay un CNAME de `www` en la zona, asi que la direccion con `www` existe y la
teclea gente. Lo que decide si funciona no es el middleware que la redirige,
sino `ALLOWED_HOSTS`: `request.get_host()` lanza `DisallowedHost` --y Django
contesta 400-- **antes** de que ningun middleware propio llegue a mirar el
host. Con el `www` fuera de la lista, la redireccion existe y no se ejecuta
nunca.

Esto se descubrio leyendo el log de produccion: entre los `DisallowedHost` de
`mail.propensionesabogados.com` --que son de cPanel y son correctos-- estaba
el del `www`, que no lo era.
"""

from django.test import SimpleTestCase, TestCase, override_settings


@override_settings(
    ALLOWED_HOSTS=['propensionesabogados.com', 'www.propensionesabogados.com'],
    SECURE_SSL_REDIRECT=False,
)
class WWWRedirectTests(TestCase):
    def test_el_www_redirige_a_la_direccion_sin_www(self):
        respuesta = self.client.get(
            '/', HTTP_HOST='www.propensionesabogados.com', secure=True
        )

        self.assertEqual(respuesta.status_code, 301)
        self.assertEqual(
            respuesta['Location'], 'https://propensionesabogados.com/'
        )

    def test_la_redireccion_conserva_la_ruta_y_la_consulta(self):
        """
        Un enlace compartido al `www` tiene que llevar a donde apunta, no a la
        portada: si no, quien lo abre pierde lo que le mandaron.
        """
        respuesta = self.client.get(
            '/consultar/proceso/?identification=123',
            HTTP_HOST='www.propensionesabogados.com',
            secure=True,
        )

        self.assertEqual(
            respuesta['Location'],
            'https://propensionesabogados.com/consultar/proceso/?identification=123',
        )

    def test_la_direccion_buena_no_redirige(self):
        respuesta = self.client.get(
            '/', HTTP_HOST='propensionesabogados.com', secure=True
        )

        self.assertNotEqual(respuesta.status_code, 301)


@override_settings(ALLOWED_HOSTS=['propensionesabogados.com'])
class HostNoPermitidoTests(TestCase):
    def test_un_nombre_de_cpanel_se_rechaza(self):
        """
        `mail.`, `webmail.`, `cpanel.`… apuntan a la misma IP pero no son de
        esta aplicacion. Que Django los rechace es lo que toca; lo que no hay
        que hacer es meterlos en `ALLOWED_HOSTS` para callar el log.
        """
        respuesta = self.client.get(
            '/', HTTP_HOST='mail.propensionesabogados.com', secure=True
        )

        self.assertEqual(respuesta.status_code, 400)


class OrdenDelMiddlewareTests(SimpleTestCase):
    def test_el_redirector_del_www_va_antes_que_la_sesion(self):
        """
        Una peticion al `www` se contesta con un 301 y nada mas. Detras de la
        sesion, la auditoria y el CSRF, se le abre sesion y se le anota una
        entrada de auditoria a algo que solo se va a redirigir.
        """
        from django.conf import settings

        orden = list(settings.MIDDLEWARE)

        self.assertLess(
            orden.index('apps.common.utils.middleware.RedirectWWWMiddleware'),
            orden.index('django.contrib.sessions.middleware.SessionMiddleware'),
        )

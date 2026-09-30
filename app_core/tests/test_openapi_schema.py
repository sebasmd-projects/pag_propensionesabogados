"""
El esquema OpenAPI se puede generar, y `check --deploy` no falla por el.

`drf_spectacular.E001` ("Schema generation threw exception") salia solo en
`manage.py check --deploy`. Causa: `ClientViewSet.get_authenticators()` leia
`self.request.method` para elegir el autenticador, pero drf-spectacular
construye la vista **con `request = None`** y llama a `initialize_request()`
antes de asignarle la peticion simulada, de modo que `self.request` era
`None` y saltaba un `AttributeError`. En una peticion de verdad no pasaba
(Django deja `self.request` puesto antes de despachar), por eso nadie lo vio
navegando: solo fallaba al generar el esquema, o sea en `check --deploy`, en
`manage.py spectacular` y en `/api/schema/` (que daba 500).

El arreglo toma el metodo de la peticion que recibe `initialize_request()`,
que es la misma que usa DRF, y no cambia el comportamiento de ninguna ruta.
"""

from django.core import checks
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from drf_spectacular.drainage import GENERATOR_STATS
from drf_spectacular.generators import SchemaGenerator

from apps.common.utils.testing import login_with_otp
from apps.project.common.users.models import UserModel


class QuietSchema:
    """
    Los avisos de drf-spectacular (sin `OpenApiAuthenticationExtension`,
    serializadores sin adivinar...) son de calidad de la documentacion y se
    listan en `docs/SEGURIDAD.md`; aqui solo estorbarian en la salida de la
    suite. Lo que se comprueba es que el esquema se genera.
    """

    def setUp(self):
        super().setUp()
        silence = GENERATOR_STATS.silence()
        silence.__enter__()
        self.addCleanup(silence.__exit__, None, None, None)


class SchemaGenerationTests(QuietSchema, TestCase):

    def test_the_schema_generates_without_a_request(self):
        """Como lo hacen `check --deploy` y `manage.py spectacular`."""
        schema = SchemaGenerator().get_schema(request=None, public=True)

        self.assertIn('/api/v1/clients/', schema['paths'])
        self.assertIn('/api/v1/clients/{id}/', schema['paths'])

    def test_check_deploy_reports_no_spectacular_error(self):
        problems = checks.run_checks(include_deployment_checks=True)

        errors = [
            problem for problem in problems
            if problem.id.startswith('drf_spectacular')
            and problem.level >= checks.ERROR
        ]

        self.assertEqual(errors, [], errors)

    def test_the_client_routes_keep_their_authentication(self):
        """
        Lo que decide el autenticador --leer/modificar un formulario por su
        dueno, crear uno nuevo con la clave de servidor-- no cambia.
        """
        from apps.project.api.platform.auth_platform.authentication import \
            LookupOrPlatformTokenAuthentication
        from apps.project.api.platform.calculator.api.views import \
            ClientViewSet
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()

        for method, action, special in (
            ('get', 'retrieve', True),
            ('put', 'update', True),
            ('patch', 'partial_update', True),
            ('post', 'create', False),
        ):
            view = ClientViewSet(action_map={method: action})
            view.initialize_request(getattr(factory, method)('/x/'))

            kinds = {type(item) for item in view.get_authenticators()}

            self.assertEqual(
                LookupOrPlatformTokenAuthentication in kinds, special,
                (method, action))


@override_settings(SECURE_SSL_REDIRECT=False)
class DocsPagesTests(QuietSchema, TestCase):
    """El esquema y las dos paginas que lo pintan responden al personal."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.staff = UserModel.objects.create_user(
            username='doc', email='doc@example.test', password='pw-Tests-123!',
            first_name='Doc', last_name='Staff', is_staff=True)
        login_with_otp(self.client, self.staff)

    def test_the_schema_endpoint_serves_the_schema(self):
        response = self.client.get(reverse('schema'), {'format': 'json'})

        self.assertEqual(response.status_code, 200)

    def test_swagger_loads_pinned_and_signed_assets(self):
        response = self.client.get(reverse('swagger-ui'))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('swagger-ui-dist@5.33.0/swagger-ui-bundle.js', html)
        self.assertNotIn('@latest', html)
        self.assertEqual(html.count('integrity="sha384-'), 3)

    def test_redoc_loads_a_pinned_and_signed_script(self):
        response = self.client.get(reverse('redoc'))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('redoc@2.5.4/bundles/redoc.standalone.js', html)
        self.assertNotIn('@latest', html)
        self.assertEqual(html.count('integrity="sha384-'), 1)

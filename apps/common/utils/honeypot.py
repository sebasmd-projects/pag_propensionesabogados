"""
La trampa para robots del formulario de contacto.

Que hace
--------
Se pinta un campo de texto que una persona no ve --posicionado fuera de la
vista, con su etiqueta explicando que se deje en blanco-- y que un robot que
rellena todo lo que encuentra si completa. Si llega con contenido, la peticion
se rechaza con 400 antes de tocar la vista.

Por que esta aqui y no viene de un paquete
------------------------------------------
Hasta ahora lo daba `django-honeypot`. Su ultima version compatible con este
Python (3.11) declara `django<5.2`, y al subir a Django 5.2 eso dejo
`pip install -r requirements.txt` sin solucion posible:

    ERROR: ResolutionImpossible
    The user requested Django==5.2.17
    django-honeypot 1.2.1 depends on Django<5.2 and >=3.2

El despliegue --produccion y cPanel-- instala con **pip**, y pip no lee
`[tool.uv]`, asi que un override en `pyproject.toml` sirve en el portatil y no
donde hace falta. La 1.3.0 si soporta Django 5.2, pero exige Python 3.12, y
cambiar el interprete de un alojamiento compartido es otra decision y otro
riesgo.

El paquete entero que se usaba eran un decorador y una etiqueta de plantilla,
que es lo que hay aqui. Traerlo adentro quita el techo en vez de esquivarlo, y
funciona igual con pip que con uv, en cualquier version de Python.

Compatibilidad
--------------
La interfaz es la misma --`check_honeypot`, `honeypot_exempt`,
`{% render_honeypot_field %}`, `HONEYPOT_FIELD_NAME`, `HONEYPOT_VALUE`,
`HONEYPOT_VERIFIER`, `HONEYPOT_RESPONDER`--, asi que las plantillas y las
vistas que ya lo usaban no cambian. Si algun dia el paquete vuelve a ser
instalable, se quita esto y se cambia el import.
"""

from functools import wraps

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.template.loader import render_to_string


def honeypot_equals(value) -> bool:
    """
    El comprobador por defecto: el campo tiene que llegar **vacio**.

    `HONEYPOT_VALUE` puede ser una cadena o algo invocable, por si alguna vez
    interesa un valor que cambie en cada peticion.
    """
    expected = getattr(settings, 'HONEYPOT_VALUE', '')
    if callable(expected):
        expected = expected()
    return value == expected


def honeypot_error(request, context):
    """La respuesta por defecto cuando la trampa se dispara."""
    return HttpResponseBadRequest(
        render_to_string(
            'honeypot/honeypot_error.html', context=context, request=request
        )
    )


def verify_honeypot_value(request, field_name):
    """
    Comprueba la trampa en un `POST`. Devuelve la respuesta de error, o `None`.

    **El campo que falta cuenta como fallo**, no como ausencia: quitarlo del
    formulario antes de enviar es justo lo que haria quien va a saltarse la
    trampa, y seria mas facil que rellenarlo.
    """
    verifier = getattr(settings, 'HONEYPOT_VERIFIER', honeypot_equals)
    responder = getattr(settings, 'HONEYPOT_RESPONDER', honeypot_error)

    if request.method != 'POST':
        return None

    field = field_name or settings.HONEYPOT_FIELD_NAME
    if field not in request.POST or not verifier(request.POST[field]):
        return responder(request, {'fieldname': field})
    return None


def check_honeypot(func=None, field_name=None):
    """
    Decora una vista para que compruebe la trampa antes de atender el `POST`.

    Se puede usar de las tres formas de siempre::

        @check_honeypot
        @check_honeypot('otro_campo')
        @check_honeypot(field_name='otro_campo')

    Sin nombre de campo usa `settings.HONEYPOT_FIELD_NAME`.
    """
    # Llamado como `@check_honeypot('campo')`: el primer posicional es el
    # nombre del campo, no la vista.
    if isinstance(func, str):
        func, field_name = field_name, func

    def decorate(view):
        @wraps(view)
        def inner(request, *args, **kwargs):
            return (
                verify_honeypot_value(request, field_name)
                or view(request, *args, **kwargs)
            )

        return inner

    return decorate if func is None else decorate(func)


def honeypot_exempt(view):
    """Marca una vista para que no se le compruebe la trampa."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        return view(*args, **kwargs)

    wrapped.honeypot_exempt = True
    return wrapped

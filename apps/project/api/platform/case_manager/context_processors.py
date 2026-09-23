"""
Lo que la cabecera del sitio necesita saber del gestor.

Por que un procesador de contexto y no un filtro de plantilla
--------------------------------------------------------------
La cabecera (`partials/header.html`) se pinta en **todas** las paginas, y
tiene que decidir si ensena el enlace al gestor. Un filtro obligaria a cargar
la biblioteca de etiquetas de esta aplicacion desde una plantilla de
`common.core`, que es la capa de abajo; declarado en `settings.py` el
acoplamiento se ve de un vistazo y se quita de un vistazo.

Lo que cuesta
-------------
Una consulta por peticion, y solo para quien ha iniciado sesion y no es
superusuario: `can_use_case_manager()` corta antes en los otros dos casos
--visitante anonimo y superusuario-- que son la inmensa mayoria de las
peticiones del sitio.
"""

from .access import can_use_case_manager


def gestor_access(request):
    """Si quien mira puede entrar al gestor."""
    return {
        'can_use_case_manager': can_use_case_manager(
            getattr(request, 'user', None)
        )
    }

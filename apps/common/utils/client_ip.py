"""
De que direccion viene una peticion, contestado en un solo sitio.

Por que esto no puede estar escrito dos veces
---------------------------------------------
Ya habia una respuesta en `case_manager.attempts.client_ip` y el middleware
de peticiones sospechosas usaba otra (`REMOTE_ADDR` a secas). Mientras no
haya proxy delante las dos coinciden, asi que la diferencia no se nota; el
dia que se declare uno dejarian de coincidir y el contador de intentos
frenaria a una direccion distinta de la que el middleware bloquea. Un limite
que cuenta una cosa y castiga otra no frena nada.

Con `django-axes` el problema se multiplica: la biblioteca trae **su propia**
deteccion de IP, asi que sin enchufarle esta habria tres.

Por que no se cree `X-Forwarded-For` por defecto
------------------------------------------------
Esa cabecera la pone quien llama. Sin un proxy propio delante que la
reescriba, creersela es dejar que cada intento elija su identidad: cambiarla
en cada peticion salta cualquier contador por IP. Solo se mira cuando el
despliegue declara que hay un proxy de confianza (`USE_X_FORWARDED_FOR`), y
entonces se toma el **primer** valor, que es el cliente original.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """
    La IP del cliente, vacia si no se puede saber.

    Nunca lanza: esto se llama desde middlewares y desde formularios de
    acceso, y un fallo aqui dejaria la pagina sin poder responder.
    """
    if request is None:
        return ''

    meta = getattr(request, 'META', None) or {}

    if getattr(settings, 'USE_X_FORWARDED_FOR', False):
        forwarded = meta.get('HTTP_X_FORWARDED_FOR', '')

        if forwarded:
            return forwarded.split(',')[0].strip()

    return meta.get('REMOTE_ADDR', '') or ''


def is_whitelisted(ip: str) -> bool:
    """
    Si esa direccion esta en la lista blanca del proyecto.

    `WhiteListedIPModel` es el remedio documentado cuando alguien queda
    bloqueado por error. Existia y el bloqueo de acceso no la conocia: anadir
    la IP levantaba la mitigacion anti-escaneo y dejaba el login igual de
    cerrado.
    """
    if not ip:
        return False

    from .models import WhiteListedIPModel

    return WhiteListedIPModel.objects.filter(
        current_ip=ip, is_active=True
    ).exists()

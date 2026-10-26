"""
El cupo del formulario de contacto, que tiene dos puertas y un solo cubo.

El contacto se puede enviar por la portada (`core:index`) y por la API
(`api-contact-create`), que es lo que llama el frontend de Next. Son dos
caminos al mismo `ContactModel`, asi que comparten cupo: con uno por puerta,
quien ataca tendria el doble repartido entre las dos.

Por que el fallo es **cerrado** (el defecto de `RateLimit`)
-----------------------------------------------------------
La portada manda un correo de confirmacion a la direccion que se escriba en el
formulario. Sin limite, repetirlo con el correo de otra persona le llena la
bandeja y quema la cuota del proveedor de correo: es el mismo caso que la
recuperacion de contrasena, y por la misma razon el limite **es** el control.
Si la cache no responde, el formulario se rechaza; una molestia pasajera, frente
a un buzon ajeno inundado.

El cupo es por IP, sin `scope`: quien envia no elige a quien perjudica, y la
IP la resuelve `get_client_ip` (que cree `X-Client-IP` solo con la clave de
servidor del proxy de Next, no una cabecera cualquiera).

Aviso: el contador vive en cache. Con `LocMemCache` (sin `REDIS_URL`) es **por
proceso**, asi que el limite real es este por el numero de workers.
"""

from apps.common.utils.throttling import RateLimit

#: Envios por IP y ventana. Diez por hora: cualquier persona real escribe una
#: o dos veces (y se equivoca alguna), y un robot que prueba a ver que pasa se
#: queda sin cupo en el undecimo.
CONTACT_MAX_PER_IP = 10
CONTACT_WINDOW_SECONDS = 60 * 60

contact_by_ip = RateLimit(
    'contact_ip',
    limit=CONTACT_MAX_PER_IP,
    window=CONTACT_WINDOW_SECONDS,
)

#: Lo que responde la API al agotarse el cupo. El mismo texto que el resto de
#: las rutas publicas de la API (`auth_platform`).
TOO_MANY_REQUESTS_DETAIL = {
    'detail': 'Demasiadas solicitudes. Intente más tarde.',
}

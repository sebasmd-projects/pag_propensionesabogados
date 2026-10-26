from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from apps.common.utils.throttling import RateLimit

from ..models import PQRSModel
from .serializers import PQRSModelSerializer

from drf_spectacular.utils import extend_schema

#: Radicados por IP y ventana. Cinco por hora: una persona radica una o dos
#: peticiones, y quien llega a seis desde la misma conexion esta llenando la
#: tabla, no ejerciendo un derecho.
#:
#: Falla **abierto**, y es la unica excepcion de los formularios publicos. Una
#: PQRS es el canal por el que alguien presenta una peticion, queja o reclamo
#: al despacho; si la cache se cae y el formulario se cierra, esa persona pierde
#: la forma de radicar justo cuando no sabe por que. Y lo que el limite evita
#: aqui es ruido en una tabla: no manda correo a nadie ni consulta nada que
#: otra persona no pueda ver, asi que aguantar el abuso durante una averia
#: cuesta menos que cerrar un canal de atencion al cliente. La averia queda en
#: el log (`RateLimit` registra que el limite NO se esta aplicando).
pqrs_by_ip = RateLimit(
    'pqrs_ip',
    limit=5,
    window=60 * 60,
    fail_open=True,
    reason='canal de radicacion de PQRS: cerrarlo por una averia de la cache '
           'deja a la gente sin poder radicar, y el limite solo evita ruido '
           'en una tabla (no manda correo ni expone datos)',
)

#: El mismo texto que el resto de las rutas publicas de la API.
TOO_MANY_REQUESTS_DETAIL = {'detail': 'Demasiadas solicitudes. Intente más tarde.'}


@extend_schema(tags=['PQRS Attlas'])
class PQRSModelCreateAPIView(CreateAPIView):
    # La recepción de PQRS está disponible para cualquier visitante.
    permission_classes = [AllowAny]

    serializer_class = PQRSModelSerializer
    queryset = PQRSModel.objects.all()

    def create(self, request, *args, **kwargs):
        # Antes de validar el cuerpo: acertar y fallar cuestan lo mismo.
        if not pqrs_by_ip.consume(request):
            return Response(TOO_MANY_REQUESTS_DETAIL, status=429)

        return super().create(request, *args, **kwargs)

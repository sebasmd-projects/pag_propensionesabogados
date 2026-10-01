"""
Sin endpoints todavia.

El gestor interno se sirve con vistas de Django y sesion (ver `access.py`), no
con DRF: no hay ningun consumidor que no sea el propio navegador del despacho,
y una API publica seria una segunda puerta que proteger sin nadie que la use.

El fichero existe porque `app_core/urls.py` monta `<app>.api.urls` en
`api/v1/` para toda app que tenga un paquete `api`, y borrar el paquete
tendria que ir acompanado de esa condicion.
"""

app_name = 'case_manager_api'

urlpatterns = []

"""
El backend de MySQL de siempre, con los UUID guardados como estaban.

El problema
-----------
Django 5.0 empezo a usar el tipo nativo ``uuid`` de MariaDB, y no lo anuncia
como un cambio de datos sino como una mejora. El interruptor esta aqui:

    # django/db/backends/mysql/features.py
    @cached_property
    def has_native_uuid_field(self):
        is_mariadb = self.connection.mysql_is_mariadb
        return is_mariadb and self.connection.mysql_version >= (10, 7)

    # django/db/backends/mysql/base.py
    if self.features.has_native_uuid_field:
        _data_types["UUIDField"] = "uuid"

Y de ahi cuelga como se escribe **cada valor** en cada consulta:

    # django/db/models/fields/__init__.py, UUIDField.get_db_prep_value
    if connection.features.has_native_uuid_field:
        return value          # con guiones: 'd717d90c-5e8c-45a7-...'
    return value.hex          # sin guiones: 'd717d90c5e8c45a7...'

Una base creada con Django 4.2 tiene la columna como ``char(32)`` y los
valores en hex **sin guiones**. Al subir a 5.x sobre MariaDB 10.7 o superior,
las consultas pasan a mandar el UUID **con guiones** contra esa misma columna,
y no coinciden con nada.

Aqui hay cuatro modulos con clave primaria ``UUIDField`` --``users``,
``core``, ``auth_platform`` e ``insolvency_form``-- y siete migraciones que
las crearon, todas escritas bajo Django 4.2.

Como se ve desde fuera
----------------------
No como un error: como un silencio. La fila existe, se lee bien, y
``filter(username=...)`` la encuentra; solo falla lo que busca **por clave
primaria**. En el acceso eso significa que la contrasena se acepta --el
backend de ``apps/common/utils/backend`` busca por ``username`` o por
``email``-- y acto seguido la sesion no puede recargar al usuario por su pk.

Por que se apaga en vez de migrar la base
-----------------------------------------
Migrar seria convertir esas columnas **y todas las claves ajenas que apuntan
a ellas** en una base en produccion, de una sola vez y sin poder volver atras
a mitad. El tipo nativo no aporta nada que este proyecto use: lo que aporta es
que MariaDB muestre el UUID formateado.

Apagarlo devuelve exactamente el comportamiento con el que se escribieron
esos datos, no inventa uno nuevo, y es reversible: quitar esto y migrar la
base sigue siendo posible el dia que compense.

En MySQL (el de Oracle, no MariaDB) esto no cambia nada: alli
``has_native_uuid_field`` ya es ``False``.
"""

from django.db.backends.mysql import base
from django.db.backends.mysql.features import DatabaseFeatures as MySQLFeatures


class DatabaseFeatures(MySQLFeatures):
    """Como antes de Django 5.0: los UUID van en ``char(32)``, en hex."""

    #: Sustituye al `cached_property` del padre. No es una opinion sobre
    #: MariaDB: es que los datos que ya hay estan escritos asi.
    has_native_uuid_field = False


class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures

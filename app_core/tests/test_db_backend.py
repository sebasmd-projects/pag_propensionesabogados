"""
Que el motor de base de datos que se instala sea el que guarda los UUID como
estaban.

Es una prueba de una linea de codigo, y aun asi es de las que mas cubren: si
`engine_for()` deja de sustituir el motor de MySQL, el sintoma en produccion no
es un error sino un acceso que se acepta y acto seguido se pierde. El porque
completo esta en `app_core/db/mysql/base.py`.
"""

import unittest

from django.test import SimpleTestCase

from app_core.db import MYSQL, PROPENSIONES_MYSQL, engine_for

try:  # El driver no esta donde la suite corre sobre SQLite.
    from django.db.backends.mysql import base as django_mysql
except Exception:  # pragma: no cover - depende del entorno, no del codigo
    django_mysql = None

necesita_mysqlclient = unittest.skipIf(
    django_mysql is None,
    'mysqlclient no esta instalado: el backend de MySQL no se puede importar',
)


class EngineForTests(SimpleTestCase):
    def test_mysql_se_sustituye_por_el_propio(self):
        """El de Django no se instala nunca: se instala el de `app_core/db`."""
        self.assertEqual(engine_for(MYSQL), PROPENSIONES_MYSQL)

    def test_los_demas_motores_se_quedan_como_estan(self):
        """El cambio es de MySQL. En PostgreSQL el UUID es nativo desde siempre."""
        for declarado in (
            'django.db.backends.postgresql',
            'django.db.backends.sqlite3',
            'django.db.backends.oracle',
        ):
            with self.subTest(declarado=declarado):
                self.assertEqual(engine_for(declarado), declarado)

    @necesita_mysqlclient
    def test_el_motor_propio_apaga_el_uuid_nativo(self):
        """
        La diferencia con el backend de Django, que es toda la razon de
        existir del modulo.
        """
        from app_core.db.mysql.base import DatabaseFeatures

        self.assertIs(DatabaseFeatures.has_native_uuid_field, False)

    @necesita_mysqlclient
    def test_el_motor_propio_es_el_de_mysql_con_esa_unica_diferencia(self):
        """No es un backend nuevo: es el de Django con una caracteristica menos."""
        from app_core.db.mysql.base import DatabaseWrapper

        self.assertTrue(issubclass(DatabaseWrapper, django_mysql.DatabaseWrapper))

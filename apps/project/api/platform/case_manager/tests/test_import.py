"""
La importacion de lo que hay en `localStorage`.

Esta es la unica oportunidad de traer lo que el despacho lleva cargado: si el
comando se equivoca, lo que se pierde no se puede volver a sacar de ningun
sitio, porque el origen es la cache de un navegador.

De ahi que lo que mas se prueba aqui no sea el camino feliz sino los datos
torcidos: el JSON lo escribio un formulario sin validacion durante meses.
"""

import json
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from ..choices import Mandate, Stage
from ..models import CaseFinanceModel, CaseModel, ClientModel


def write(tmp_path, data):
    path = tmp_path / 'propdemo.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


class ImportPropDemoTests(TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        self.tmp = Path(tempfile.mkdtemp())

    def run_import(self, data, *args):
        out, err = StringIO(), StringIO()
        call_command(
            'import_propdemo', str(write(self.tmp, data)),
            *args, stdout=out, stderr=err,
        )
        return out.getvalue(), err.getvalue()

    # --- el camino normal -------------------------------------------------
    def test_importa_cliente_caso_y_dinero(self):
        self.run_import({
            '16484186': {
                'n': 'Carlos Emiro Giraldo Lozada',
                's': 'Representación judicial',
                't': 'Proceso ordinario',
                'a': 'Civil',
                'st': 'Responsabilidad civil',
                'e': 2,
                'v': 'activo',
                'r': '2026-00145-00',
                'mm': 'Modalidad de pago',
                'hp': 6_000_000,
                'ge': 2_000_000,
            },
        })

        client = ClientModel.objects.get(identification='16484186')
        case = client.cases.get()

        self.assertEqual(client.full_name, 'Carlos Emiro Giraldo Lozada')
        self.assertTrue(client.is_active)
        self.assertEqual(case.stage, Stage.IN_PROGRESS)
        self.assertEqual(case.case_number, '2026-00145-00')
        self.assertEqual(case.finance.balance, 4_000_000)

    def test_la_cuota_litis_sobre_cero_llega_como_expectativa(self):
        self.run_import({
            '52147896': {
                'n': 'Marta Rios',
                'mm': 'Cuota litis',
                'pl': 30,
                'vl': 9_000_000,
            },
        })

        finance = CaseFinanceModel.objects.get()

        self.assertEqual(finance.expectation, 9_000_000)
        self.assertEqual(finance.balance, 0)

    def test_inactivo_sigue_inactivo(self):
        self.run_import({'999': {'n': 'Rosa', 'v': 'inactivo'}})

        self.assertFalse(ClientModel.objects.get().is_active)

    def test_volver_a_importar_no_duplica(self):
        data = {'16484186': {'n': 'Carlos', 's': 'Conciliación'}}
        self.run_import(data)
        self.run_import(data)

        self.assertEqual(ClientModel.objects.count(), 1)
        self.assertEqual(CaseModel.objects.count(), 1)

    # --- los datos torcidos ----------------------------------------------
    def test_una_etapa_fuera_de_rango_no_adelanta_el_caso(self):
        """
        Inventar una etapa mas avanzada le diria al cliente que su asunto va
        por donde no va. Se queda en la primera.
        """
        self.run_import({'999': {'n': 'Rosa', 'e': 9}})

        self.assertEqual(
            CaseModel.objects.get().stage, Stage.DOCUMENTS_RECEIVED
        )

    def test_un_importe_escrito_como_texto_se_entiende(self):
        """El campo del navegador no validaba nada: guardaba cadenas."""
        self.run_import({
            '999': {
                'n': 'Rosa', 'mm': 'Modalidad de pago',
                'hp': '6000000', 'ge': '2000000',
            },
        })

        self.assertEqual(CaseFinanceModel.objects.get().balance, 4_000_000)

    def test_un_importe_ilegible_es_cero_y_no_detiene_la_importacion(self):
        self.run_import({
            '999': {'n': 'Rosa', 'mm': 'Modalidad de pago', 'hp': 'mucho'},
            '888': {'n': 'Pedro', 'mm': 'Modalidad de pago', 'hp': 1_000_000},
        })

        self.assertEqual(ClientModel.objects.count(), 2)
        self.assertEqual(
            CaseFinanceModel.objects.get(
                case__client__identification='999'
            ).agreed_fee,
            0,
        )

    def test_una_modalidad_desconocida_no_importa_dinero_pero_si_el_caso(self):
        _, err = self.run_import({
            '999': {'n': 'Rosa', 'mm': 'Modalidad inventada', 'hp': 100},
        })

        self.assertIn('modalidad desconocida', err)
        self.assertEqual(CaseModel.objects.count(), 1)
        self.assertFalse(CaseFinanceModel.objects.exists())

    def test_sin_cedula_o_sin_nombre_se_omite(self):
        out, err = self.run_import({
            '': {'n': 'Sin cedula'},
            '999': {'n': ''},
            '888': {'n': 'Pedro'},
        })

        self.assertEqual(ClientModel.objects.count(), 1)
        self.assertIn('2 omitidos', out)

    def test_la_cedula_con_puntos_se_normaliza(self):
        self.run_import({'16.484.186': {'n': 'Carlos'}})

        self.assertTrue(
            ClientModel.objects.filter(identification='16484186').exists()
        )

    # --- el ensayo y los errores -----------------------------------------
    def test_el_ensayo_no_escribe_nada(self):
        out, _ = self.run_import({'999': {'n': 'Rosa'}}, '--dry-run')

        self.assertIn('Ensayo', out)
        self.assertFalse(ClientModel.objects.exists())

    def test_un_fichero_que_no_existe_lo_dice(self):
        with self.assertRaises(CommandError):
            call_command('import_propdemo', str(self.tmp / 'no-existe.json'))

    def test_un_json_roto_lo_dice(self):
        path = self.tmp / 'roto.json'
        path.write_text('{esto no es json', encoding='utf-8')

        with self.assertRaises(CommandError):
            call_command('import_propdemo', str(path))

    def test_un_json_que_no_es_un_objeto_lo_dice(self):
        path = self.tmp / 'lista.json'
        path.write_text('[1, 2, 3]', encoding='utf-8')

        with self.assertRaises(CommandError):
            call_command('import_propdemo', str(path))


class SetupGroupTests(TestCase):
    """El grupo del gestor y sus permisos."""

    def test_crea_el_grupo_con_sus_permisos(self):
        from django.contrib.auth.models import Group

        from ..access import GESTOR_GROUP

        call_command('setup_case_manager_group', stdout=StringIO())

        group = Group.objects.get(name=GESTOR_GROUP)
        codenames = set(group.permissions.values_list('codename', flat=True))

        self.assertIn('change_casemodel', codenames)
        self.assertIn('add_clientmodel', codenames)

    def test_no_concede_permiso_de_borrado(self):
        """
        No hay papelera --esta fuera del alcance-- y borrar un cliente se
        lleva por delante sus casos y su historial financiero. Para dar de
        baja esta la vigencia.
        """
        from django.contrib.auth.models import Group

        from ..access import GESTOR_GROUP

        call_command('setup_case_manager_group', stdout=StringIO())

        codenames = set(
            Group.objects.get(name=GESTOR_GROUP).permissions.values_list(
                'codename', flat=True
            )
        )

        self.assertNotIn('delete_clientmodel', codenames)
        self.assertNotIn('delete_casemodel', codenames)

    def test_se_puede_ejecutar_dos_veces(self):
        call_command('setup_case_manager_group', stdout=StringIO())
        call_command('setup_case_manager_group', stdout=StringIO())

        from django.contrib.auth.models import Group

        from ..access import GESTOR_GROUP

        self.assertEqual(Group.objects.filter(name=GESTOR_GROUP).count(), 1)

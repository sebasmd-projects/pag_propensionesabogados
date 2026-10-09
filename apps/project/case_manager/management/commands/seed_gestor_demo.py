"""
Datos de demostracion para el gestor de casos (`/gestor/`).

Sirve para validar a mano el panel financiero y todos los flujos del gestor
sobre una base local vacia. Todo es ficticio: nombres inventados, cedulas que
empiezan por `9990` (el marcador de este comando), correos `@example.com` y
telefonos que no existen.

    manage.py seed_gestor_demo
    manage.py seed_gestor_demo --user ia_test_user

Reglas del comando
------------------
- **Idempotente.** Un cliente cuya cedula ya existe se salta entero (con sus
  asuntos): ejecutarlo dos veces no duplica nada.
- **Nunca borra**, ni lo suyo ni lo que haya en la base.
- Todo pasa por `full_clean()`: si el modelo cambia y algun dato deja de ser
  valido, el comando falla en vez de dejar basura.
- Los importes son siempre de 1.000.000 COP o mas (o cero, que es "no hay").
- `--user` solo añade al usuario al grupo del gestor; no toca su contrasena ni
  ningun otro atributo.
"""

from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.project.case_manager import choices
from apps.project.case_manager.access import GESTOR_GROUP
from apps.project.case_manager.identification import     nit_check_digit
from apps.project.case_manager.models import (CaseFinanceModel,
                                                           CaseModel,
                                                           CaseNoteModel,
                                                           ClientModel)

#: Marcador: todas las cedulas de demostracion empiezan por esto.
PREFIX = '9990'

S = choices.Service
M = choices.Mandate
K = choices.NoteKind
MILLION = 1_000_000


# ---------------------------------------------------------------------------
# Filas del historial de pagos (mismo formato que produce el formulario).
# ---------------------------------------------------------------------------

def A(amount, when):
    """Pago administrativo (uno por asunto, como mucho)."""
    return {'kind': 'administrative', 'amount': amount, 'date': when.isoformat(),
            'next_date': '', 'legacy': False}


def P(amount, when, next_date=None):
    """Abono con fecha."""
    return {'kind': 'payment', 'amount': amount, 'date': when.isoformat(),
            'next_date': next_date.isoformat() if next_date else '',
            'legacy': False}


def L(amount):
    """Abono antiguo, sin fecha (importado): el modelo lo admite."""
    return {'kind': 'payment', 'amount': amount, 'date': '', 'next_date': '',
            'legacy': True}


def E(amount, when):
    """Proximo pago programado."""
    return {'kind': 'expected', 'amount': amount, 'date': when.isoformat(),
            'next_date': '', 'legacy': False}


def d(year, month, day):
    return date(year, month, day)


def N(kind, title, body, when, visible=True, notified=False):
    return {'kind': kind, 'title': title, 'body': body, 'when': when,
            'visible': visible, 'notified': notified}


def C(**kw):
    """Un asunto. Las claves son las del modelo mas `mandate` y los importes."""
    kw.setdefault('mandate', M.PAYMENT)
    return kw


# ---------------------------------------------------------------------------
# Escenarios escritos a mano
# ---------------------------------------------------------------------------

def handmade_clients():
    return [
        dict(n=1, name='Marta Lucía Ospina Garzón', email='marta.ospina@example.com',
             phone='3005550101', cases=[
                 C(service=S.JUDICIAL, subtype='Familia',
                   second_subtype='Divorcio / cesación de efectos civiles',
                   area='Familia', procedure='Proceso ordinario',
                   instance='Primera instancia', stage=2,
                   court='Juzgado Municipal', city='Bogotá D.C.',
                   case_number='11001-31-10-005-2022-00412-00',
                   start=d(2022, 2, 7), fee=12 * MILLION,
                   history=[A(1_500_000, d(2022, 2, 10)),
                            P(3 * MILLION, d(2022, 3, 15)),
                            P(3 * MILLION, d(2022, 6, 20)),
                            P(2 * MILLION, d(2023, 1, 10)),
                            E(1_500_000, d(2026, 11, 15)),
                            E(1 * MILLION, d(2027, 2, 15))],
                   notes=[N(K.INFO, 'Audiencia programada',
                            'Se fijó la audiencia inicial para el próximo mes.',
                            d(2026, 9, 1), notified=True),
                          N(K.DOCUMENT, 'Falta el registro civil de matrimonio',
                            'Envíenos una copia reciente del registro civil.',
                            d(2026, 9, 20), notified=True),
                          N(K.STAGE, 'Cambio de etapa: En trámite',
                            'El asunto pasó a la etapa En trámite.',
                            d(2022, 5, 3))]),
                 C(service=S.JUDICIAL, subtype='Familia', second_subtype='Alimentos',
                   area='Familia', procedure='Proceso ordinario',
                   instance='Primera instancia', stage=3,
                   court='Juzgado Municipal', city='Bogotá D.C.',
                   start=d(2024, 5, 13), mandate=M.PRO_BONO,
                   notes=[N(K.BLOCKED, 'Juzgado sin respuesta',
                            'El juzgado no ha resuelto el escrito; seguimos pendientes.',
                            d(2026, 8, 12))]),
             ]),
        dict(n=2, name='Jairo Hernán Cifuentes Mejía', email=None, phone='3005550102',
             cases=[
                 C(service=S.JUDICIAL, subtype='Laboral', second_subtype='Ordinario laboral',
                   area='Laboral', procedure='Proceso ordinario',
                   instance='Primera instancia', stage=3,
                   court='Juzgado del Circuito', city='Medellín',
                   case_number='05001-31-05-012-2022-00287-00',
                   start=d(2022, 4, 18), mandate=M.CONTINGENCY, pct=30,
                   value=180 * MILLION,
                   notes=[N(K.INFO, 'Se practicaron los testimonios',
                            'Ya se recibieron los testimonios de la parte demandante.',
                            d(2026, 7, 9), notified=True)]),
                 C(service=S.JUDICIAL, subtype='Laboral',
                   second_subtype='Pensión de sobrevivientes',
                   area='Pensional / Seguridad Social', procedure='Proceso ordinario',
                   instance='Primera instancia', stage=1,
                   court='Juzgado del Circuito', city='Medellín',
                   start=d(2025, 1, 20), mandate=M.CONTINGENCY, pct=20,
                   value=95 * MILLION,
                   notes=[N(K.INFO, 'Nota interna: revisar semanas cotizadas',
                            'Pedir historia laboral a Colpensiones antes de radicar.',
                            d(2025, 1, 27), visible=False)]),
             ]),
        dict(n=3, name='Consuelo Barrera Quintero', email='consuelo.barrera@example.com',
             phone='3005550103', cases=[
                 C(service=S.JUDICIAL, subtype='Laboral', second_subtype='Pensión de vejez',
                   area='Pensional / Seguridad Social', procedure='Proceso ordinario',
                   instance='Segunda instancia', stage=4,
                   court='Tribunal Superior', city='Cali',
                   case_number='76001-31-05-003-2023-00155-01',
                   start=d(2023, 3, 6), mandate=M.CONTINGENCY, pct=0,
                   value=45 * MILLION, paid=15 * MILLION,
                   notes=[N(K.STAGE, 'Cambio de etapa: Etapa final',
                            'El asunto pasó a la etapa final.', d(2026, 6, 2),
                            notified=True)]),
             ]),
        dict(n=4, name='Inversiones El Roble S.A.S.', email='contabilidad@elroble.example.com',
             phone='6015550104', cases=[
                 C(service=S.JUDICIAL, subtype='Civil', second_subtype='Ejecutivo',
                   area='Comercial / Empresarial', procedure='Proceso ejecutivo',
                   instance='Ejecución', stage=4,
                   court='Juzgado del Circuito', city='Barranquilla',
                   case_number='08001-31-03-007-2022-00931-00',
                   start=d(2022, 9, 5), fee=320 * MILLION,
                   history=[A(20 * MILLION, d(2022, 9, 5)),
                            P(80 * MILLION, d(2023, 3, 10)),
                            P(60 * MILLION, d(2024, 8, 22)),
                            P(50 * MILLION, d(2025, 6, 17)),
                            P(40 * MILLION, d(2026, 9, 28)),
                            E(30 * MILLION, d(2026, 10, 30)),
                            E(40 * MILLION, d(2027, 1, 29))],
                   notes=[N(K.INFO, 'Embargo de cuentas decretado',
                            'El juzgado decretó el embargo de las cuentas del deudor.',
                            d(2026, 9, 14), notified=True)]),
                 C(service=S.CONSULTING, subtype='Consultoría empresarial',
                   area='Comercial / Empresarial', procedure='Privado',
                   instance='Entregada', stage=5, start=d(2024, 1, 15),
                   fee=8_500_000, paz=True,
                   history=[P(4 * MILLION, d(2024, 2, 14)),
                            P(4_500_000, d(2024, 4, 10))]),
             ]),
        dict(n=5, name='Andrés Felipe Rincón Salcedo', email='andres.rincon@example.com',
             phone='3005550105', cases=[
                 C(service=S.CONCILIATION, subtype='Centro de conciliación',
                   area='Conciliación', procedure='Conciliación',
                   instance='Finalizada', stage=5, active=False,
                   start=d(2022, 6, 20), fee=4_500_000, paz=True,
                   history=[P(2_500_000, d(2022, 7, 12)),
                            P(2 * MILLION, d(2022, 8, 2))],
                   notes=[N(K.STAGE, 'Cambio de etapa: Finalizado',
                            'La conciliación terminó con acuerdo.', d(2022, 8, 3),
                            notified=True)]),
                 C(service=S.CONSULTING, subtype='Consultoría procesal',
                   area='Civil', procedure='Privado',
                   instance='Entregada', stage=5, start=d(2025, 2, 24),
                   fee=6 * MILLION,  # pagado por completo, paz y salvo SIN autorizar
                   history=[P(3 * MILLION, d(2025, 3, 11)),
                            P(3 * MILLION, d(2025, 4, 29))]),
             ]),
        dict(n=6, name='Luz Marina Patiño Rojas', email='luz.patino@example.com',
             phone='3005550106', cases=[
                 C(service=S.ADMINISTRATIVE, subtype='PQR / Derecho de petición',
                   area='Administrativo', procedure='Administrativo',
                   instance='Etapa inicial', stage=1,
                   sector='Público', entity='Entidad Pública Demo',
                   administrative_case_number='PQR-2026-08841',
                   administrative_city='Bogotá D.C.',
                   start=d(2026, 8, 11), fee=2_800_000,
                   history=[L(1 * MILLION), E(1_800_000, d(2026, 9, 30))],
                   notes=[N(K.DOCUMENT, 'Falta copia de la cédula',
                            'Adjunte la copia de su cédula por ambos lados.',
                            d(2026, 8, 20), notified=True)]),
                 C(service=S.ADMINISTRATIVE, subtype='Recurso de reposición',
                   area='Administrativo', procedure='Administrativo',
                   instance='Recurso', stage=2,
                   sector='Privado', entity='Empresa Privada Demo S.A.',
                   administrative_case_number='REC-2026-0192',
                   administrative_city='Bogotá D.C.',
                   start=d(2026, 9, 1), fee=3_500_000,
                   history=[A(1 * MILLION, d(2026, 9, 3)),
                            P(1 * MILLION, d(2026, 9, 10)),
                            E(1_500_000, d(2026, 10, 15))]),
             ]),
        dict(n=7, name='Fabio Nelson Cárdenas Uribe', email=None, phone='3005550107',
             active=False, cases=[
                 C(service=S.JUDICIAL, subtype='Penal', second_subtype='Defensa penal',
                   area='Penal', procedure='Proceso ordinario',
                   instance='Segunda instancia', stage=4, active=False,
                   court='Tribunal Superior', city='Ibagué',
                   case_number='73001-60-00-450-2021-01203-01',
                   start=d(2022, 1, 10), fee=18 * MILLION,  # saldo sin programar
                   history=[A(2 * MILLION, d(2022, 1, 12)),
                            P(4 * MILLION, d(2022, 5, 30))]),
             ]),
        dict(n=8, name='Diana Carolina Vélez Arango', email='diana.velez@example.com',
             phone='3005550108', cases=[
                 C(service=S.JUDICIAL, subtype='Familia', second_subtype='Filiación',
                   area='Familia', procedure='Proceso ordinario',
                   instance='Primera instancia', stage=2,
                   court='Juzgado Municipal', city='Manizales',
                   start=d(2023, 11, 6), mandate=M.GUARDIANSHIP),
                 C(service=S.CONCILIATION, subtype='Comisaría de Familia',
                   area='Familia', procedure='Conciliación',
                   instance='Solicitud presentada', stage=0,
                   start=d(2026, 9, 15), mandate=M.PRO_BONO,
                   notes=[N(K.INFO, 'Solicitud recibida',
                            'Recibimos su solicitud de conciliación.',
                            d(2026, 9, 15), notified=True)]),
             ]),
        dict(n=9, name='Héctor Julián Ramírez Botero', email='hector.ramirez@example.com',
             phone='3005550109', cases=[
                 C(service=S.CONCILIATION, subtype='Inspección de Policía',
                   area='Civil', procedure='Querella policiva',
                   instance='En negociación', stage=2,
                   police_instance='Primera instancia',
                   police_office='Inspección 4 de Policía Demo',
                   police_case_number='QP-2024-0173', police_city='Pereira',
                   start=d(2024, 2, 19), fee=6 * MILLION, dash=False,
                   history=[P(3 * MILLION, d(2024, 3, 1))],
                   notes=[N(K.DOCUMENT, 'Escritura del predio',
                            'Necesitamos la escritura registrada del predio.',
                            d(2026, 9, 5), notified=True)]),
             ]),
        dict(n=10, name='Sandra Milena Toro Giraldo', email='sandra.toro@example.com',
             phone='3005550110', cases=[
                 C(service=S.JUDICIAL, subtype='Superintendencias',
                   second_subtype='Protección al consumidor financiero',
                   area='Seguros', instance='Primera instancia', stage=1,
                   court='Superintendencia', city='Bogotá D.C.',
                   start=d(2026, 1, 19), mandate=M.CONTINGENCY, pct=40,
                   value=260 * MILLION),
                 C(service=S.CONCILIATION, subtype='Centro de conciliación',
                   area='Insolvencia', procedure='Conciliación',
                   instance='Finalizada', stage=5, start=d(2026, 3, 9),
                   mandate=M.CONTINGENCY, pct=0, value=22 * MILLION,
                   paid=22 * MILLION, paz=True),
             ]),
        dict(n=11, name='Wilson Alexander Peña Lozano', email='wilson.pena@example.com',
             phone='3005550111', cases=[
                 C(service=S.JUDICIAL, subtype='Familia', second_subtype='Sucesión',
                   area='Sucesiones', procedure='Trámite notarial',
                   instance='Primera instancia', stage=5, active=False,
                   city='Ibagué', start=d(2022, 1, 17), fee=25 * MILLION,
                   paz=True,
                   history=[A(2 * MILLION, d(2022, 1, 20)),
                            P(5 * MILLION, d(2022, 2, 25)),
                            P(6 * MILLION, d(2022, 5, 19)),
                            P(6 * MILLION, d(2022, 9, 30)),
                            P(6 * MILLION, d(2023, 2, 14))]),
             ]),
        dict(n=12, name='Gloria Esperanza Mahecha Ayala', email='gloria.mahecha@example.com',
             phone='3005550112', cases=[
                 C(service=S.JUDICIAL, subtype='Superintendencias',
                   second_subtype='Protección al consumidor',
                   area='Consumidor', instance='Primera instancia', stage=3,
                   court='Superintendencia', city='Bogotá D.C.',
                   start=d(2025, 8, 25), fee=9 * MILLION,
                   history=[A(1 * MILLION, d(2025, 9, 1)),
                            P(2 * MILLION, d(2025, 11, 4), next_date=d(2026, 10, 15)),
                            P(1 * MILLION, d(2026, 9, 22)),
                            E(1 * MILLION, d(2026, 10, 15)),
                            E(1 * MILLION, d(2026, 11, 15)),
                            E(1 * MILLION, d(2026, 12, 15)),
                            E(1 * MILLION, d(2027, 1, 15)),
                            E(1 * MILLION, d(2027, 2, 15))]),
             ]),
        dict(n=13, name='Óscar Iván Duarte Parra', email=None, phone=None, cases=[
            C(service=S.FIELD_RESEARCH, subtype='Estudio de seguridad',
              area='Investigación de campo', procedure='Investigación de campo',
              instance='En investigación', stage=3, start=d(2026, 9, 22),
              fee=7_500_000,
              history=[A(1_500_000, d(2026, 9, 22)),
                       P(1_500_000, d(2026, 9, 29)),  # hoy
                       E(4_500_000, d(2026, 10, 20))]),
        ]),
        dict(n=14, name='Yolanda Beltrán Cruz', email='yolanda.beltran@example.com',
             phone='3005550114', cases=[
                 C(service=S.OTHER, service_other='Asesoría en propiedad horizontal',
                   procedure='Otro', procedure_other='Asamblea de copropietarios',
                   area='Otro', area_other='Propiedad horizontal',
                   subtype='Otro', subtype_other='Reglamento interno',
                   instance='Inicial', stage=0, start=d(2026, 5, 4),
                   fee=3_200_000, history=[L(1_200_000)]),
                 C(service=S.CONSULTING, subtype='Consultoría procesal', area='Civil',
                   procedure='Privado', instance='En elaboración', stage=2,
                   start=d(2026, 8, 31), fee=5 * MILLION,
                   history=[P(1 * MILLION, d(2026, 9, 8)),
                            P(1 * MILLION, d(2026, 9, 15)),
                            P(1 * MILLION, d(2026, 9, 22)),
                            E(2 * MILLION, d(2026, 11, 10))]),
             ]),
        dict(n=15, name='Camilo Ernesto Zapata Ríos', email='camilo.zapata@example.com',
             phone='3005550115', cases=[
                 C(service=S.JUDICIAL, subtype='Civil', second_subtype='Reivindicatorio',
                   area='Civil', procedure='Proceso ordinario', instance='Casación',
                   stage=4, court='Tribunal Superior', city='Bogotá D.C.',
                   case_number='11001-31-03-020-2022-00733-02',
                   start=d(2022, 11, 14), mandate=M.CONTINGENCY, pct=50,
                   value=500 * MILLION),
                 C(service=S.JUDICIAL, subtype='Contencioso administrativo',
                   second_subtype='Nulidad y restablecimiento del derecho',
                   area='Administrativo', procedure='Proceso ordinario',
                   instance='Segunda instancia', stage=3,
                   court='Consejo de Estado', city='Bogotá D.C.',
                   start=d(2023, 8, 21), mandate=M.CONTINGENCY, pct=10,
                   value=120 * MILLION),
                 C(service=S.JUDICIAL, subtype='Civil', second_subtype='Responsabilidad civil',
                   area='Civil', procedure='Proceso ordinario',
                   instance='Primera instancia', stage=2,
                   court='Juzgado del Circuito', city='Bogotá D.C.',
                   start=d(2024, 3, 4), fee=45 * MILLION,
                   history=[A(5 * MILLION, d(2024, 3, 4)),
                            P(10 * MILLION, d(2024, 9, 16)),
                            P(10 * MILLION, d(2025, 4, 8)),
                            P(10 * MILLION, d(2025, 11, 24)),
                            E(10 * MILLION, d(2026, 10, 10))]),
             ]),
        dict(n=16, name='Patricia Elena Mora Cadavid', email='patricia.mora@example.com',
             phone='3005550116', cases=[
                 C(service=S.JUDICIAL, subtype='Contencioso administrativo',
                   second_subtype='Reparación directa', area='Administrativo',
                   procedure='Proceso ordinario', instance='Primera instancia',
                   stage=2, court='Juzgado Administrativo', city='Cartagena',
                   start=d(2025, 5, 12), mandate=M.CONTINGENCY, pct=0,
                   value=60 * MILLION, paid=10 * MILLION),
                 C(service=S.ADMINISTRATIVE, subtype='Acción de tutela',
                   area='Administrativo', procedure='Acción de tutela',
                   instance='Decisión definitiva', stage=5,
                   start=d(2025, 6, 23), fee=1_500_000, paz=True,
                   history=[P(1_500_000, d(2025, 7, 1))]),
             ]),
        dict(n=17, name='Rubén Darío Ocampo Henao', email=None, phone='3005550117',
             active=False, cases=[
                 C(service=S.JUDICIAL, subtype='Penal', second_subtype='Representación de víctimas',
                   area='Penal', procedure='Proceso ordinario',
                   instance='Primera instancia', stage=5, active=False,
                   court='Juzgado del Circuito', city='Cúcuta',
                   start=d(2022, 3, 1), fee=14 * MILLION,
                   history=[A(2 * MILLION, d(2022, 3, 8)),
                            P(6 * MILLION, d(2022, 8, 16)),
                            P(6 * MILLION, d(2023, 1, 31))]),
             ]),
        dict(n=18, name='Natalia Andrea Quiroga León', email='natalia.quiroga@example.com',
             phone='3005550118', cases=[
                 C(service=S.JUDICIAL, subtype='Laboral', second_subtype='Fuero sindical',
                   area='Laboral', procedure='Proceso ordinario',
                   instance='Primera instancia', stage=1,
                   court='Juzgado del Circuito', city='Bucaramanga',
                   start=d(2026, 9, 1), fee=11 * MILLION,
                   history=[A(1 * MILLION, d(2026, 9, 3)),
                            P(2 * MILLION, d(2026, 9, 10)),
                            P(2 * MILLION, d(2026, 9, 17)),
                            P(2 * MILLION, d(2026, 9, 24)),
                            E(2 * MILLION, d(2026, 10, 24)),
                            E(2 * MILLION, d(2026, 11, 24))],
                   notes=[N(K.INFO, 'Demanda radicada',
                            'Radicamos la demanda esta semana.', d(2026, 9, 24),
                            notified=True),
                          N(K.BLOCKED, 'A la espera del reparto',
                            'El despacho aún no asigna el juzgado.', d(2026, 9, 25)),
                          N(K.DOCUMENT, 'Carta de despido',
                            'Envíenos la carta de despido original.',
                            d(2026, 9, 28), notified=True),
                          N(K.STAGE, 'Cambio de etapa: En estudio',
                            'El asunto pasó a la etapa En estudio.',
                            d(2026, 9, 29))]),
             ]),
    ]


# ---------------------------------------------------------------------------
# Clientes con otro tipo de documento (NIT, CE, PA)
#
# Llevan su `identification` explicita, siempre con el marcador `9990`, y no
# `n`: el numero se guarda tal cual. Los NIT (9 digitos) llevan el DV
# calculado, no escrito a mano.
# ---------------------------------------------------------------------------

def document_clients():
    return [
        dict(identification='999012345', id_type='NIT',
             name='Construcciones Andinas S.A.S.',
             email='gerencia@andinas.example.com', phone='6015550201',
             legal_rep=dict(name='Ricardo Alfonso Mejía Torres',
                            id_type='CC', identification='79123456',
                            email='ricardo.mejia@andinas.example.com',
                            phone='3005550211'),
             cases=[
                 C(service=S.CONSULTING, subtype='Consultoría empresarial',
                   area='Comercial / Empresarial', procedure='Privado',
                   instance='Entregada', stage=5, start=d(2025, 3, 10),
                   fee=12 * MILLION, paz=True,
                   history=[P(6 * MILLION, d(2025, 4, 9)),
                            P(6 * MILLION, d(2025, 6, 11))]),
                 C(service=S.JUDICIAL, subtype='Civil', second_subtype='Ejecutivo',
                   area='Comercial / Empresarial', procedure='Proceso ejecutivo',
                   instance='Primera instancia', stage=2,
                   court='Juzgado del Circuito', city='Medellín',
                   start=d(2026, 2, 16), fee=30 * MILLION,
                   history=[A(3 * MILLION, d(2026, 2, 18)),
                            P(10 * MILLION, d(2026, 4, 20)),
                            E(8 * MILLION, d(2026, 12, 15))]),
             ]),
        dict(identification='999054321', id_type='NIT',
             name='Comercializadora del Valle Ltda.', email=None,
             phone='6025550202',
             cases=[
                 C(service=S.ADMINISTRATIVE, subtype='PQR / Derecho de petición',
                   area='Seguros', procedure='Administrativo',
                   instance='Etapa inicial', stage=1, sector='Público',
                   entity='Entidad Pública Demo NIT',
                   administrative_case_number='ADM-2026-9001',
                   administrative_city='Cali', start=d(2026, 5, 4),
                   mandate=M.CONTINGENCY, pct=20, value=60 * MILLION),
             ]),
        dict(identification='99901234', id_type='CE',
             name='Giovanni Rossi Bianchi', email='giovanni.rossi@example.com',
             phone='3005550203',
             cases=[
                 C(service=S.CONCILIATION, subtype='Conciliación privada',
                   area='Conciliación', procedure='Conciliación',
                   instance='Audiencia programada', stage=2, start=d(2026, 3, 9),
                   fee=4 * MILLION,
                   history=[P(2 * MILLION, d(2026, 3, 12)),
                            E(2 * MILLION, d(2026, 11, 10))]),
             ]),
        dict(identification='9990XY456', id_type='PA',
             name='Emily Carter Johnson', email='emily.carter@example.com',
             phone='3005550204',
             cases=[
                 C(service=S.FIELD_RESEARCH, subtype='Investigación judicial',
                   area='Investigación de campo',
                   procedure='Investigación de campo', instance='En investigación',
                   stage=2, start=d(2026, 6, 1), fee=5 * MILLION,
                   history=[P(5 * MILLION, d(2026, 6, 3))]),
             ]),
    ]


# ---------------------------------------------------------------------------
# Clientes generados: reparten inicios y pagos de enero de 2022 a hoy
# ---------------------------------------------------------------------------

FIRST_NAMES = (
    'Álvaro José', 'Beatriz Elena', 'Carlos Andrés', 'Doris Amparo',
    'Edgar Mauricio', 'Flor Alba', 'Gustavo Adolfo', 'Hilda Rosa',
    'Iván Darío', 'Judith Marcela', 'Kevin Alexis', 'Liliana Paola',
    'Mauricio Esteban', 'Nubia Stella', 'Orlando Jesús', 'Pilar Cristina',
    'Ricardo Alonso', 'Sonia Patricia', 'Tomás Eduardo', 'Úrsula Inés',
    'Víctor Manuel', 'Yesenia Lucía', 'Zulma Constanza', 'Arturo Fernando',
)
SURNAMES = (
    'Acosta', 'Bermúdez', 'Cortés', 'Devia', 'Escobar', 'Franco', 'Gaitán',
    'Herrera', 'Isaza', 'Jaramillo', 'Kerguelén', 'Londoño',
)
CITIES = ('Bogotá D.C.', 'Medellín', 'Cali', 'Barranquilla', 'Bucaramanga',
          'Cartagena', 'Pereira', 'Manizales', 'Armenia', 'Villavicencio')

#: (servicio, subtipo, segundo subtipo, area, tramite, extra)
TEMPLATES = (
    (S.JUDICIAL, 'Civil', 'Ejecutivo', 'Civil', 'Proceso ejecutivo', 'Juzgado Municipal'),
    (S.JUDICIAL, 'Laboral', 'Ordinario laboral', 'Laboral', 'Proceso ordinario', 'Juzgado del Circuito'),
    (S.JUDICIAL, 'Familia', 'Alimentos', 'Familia', 'Proceso ordinario', 'Juzgado Municipal'),
    (S.JUDICIAL, 'Penal', 'Defensa penal', 'Penal', 'Proceso ordinario', 'Tribunal Superior'),
    (S.JUDICIAL, 'Contencioso administrativo', 'Reparación directa', 'Administrativo', 'Proceso ordinario', 'Juzgado Administrativo'),
    (S.JUDICIAL, 'Superintendencias', 'Protección al consumidor', 'Consumidor', None, 'Superintendencia'),
    (S.JUDICIAL, 'Laboral', 'Pensión de invalidez', 'Pensional / Seguridad Social', 'Proceso ordinario', 'Juzgado del Circuito'),
    (S.JUDICIAL, 'Civil', 'Pertenencia / prescripción adquisitiva', 'Civil', 'Proceso ordinario', 'Juzgado Municipal'),
    (S.JUDICIAL, 'Familia', 'Sucesión', 'Sucesiones', 'Proceso ordinario', 'Juzgado Municipal'),
    (S.CONCILIATION, 'Centro de conciliación', '', 'Insolvencia', 'Conciliación', ''),
    (S.CONSULTING, 'Consultoría empresarial', '', 'Comercial / Empresarial', 'Privado', ''),
    (S.ADMINISTRATIVE, 'PQR / Derecho de petición', '', 'Seguros', 'Administrativo', 'admin'),
    (S.FIELD_RESEARCH, 'Investigación judicial', '', 'Investigación de campo', 'Investigación de campo', ''),
    (S.JUDICIAL, 'Superintendencias', 'Competencia desleal', 'Comercial / Empresarial', None, 'Superintendencia'),
    (S.CONCILIATION, 'Conciliación privada', '', 'Conciliación', 'Conciliación', ''),
)


def add_months(value, months):
    total = value.year * 12 + value.month - 1 + months
    return date(total // 12, total % 12 + 1, 1)


def generated_clients(today):
    clients = []
    for i in range(24):
        start = add_months(date(2022, 1, 1), round(i * 56 / 23)).replace(
            day=3 + (i * 7) % 25)
        start = min(start, today)
        service, sub, sub2, area, procedure, extra = TEMPLATES[i % len(TEMPLATES)]
        case = C(service=service, subtype=sub, second_subtype=sub2, area=area,
                 procedure=procedure or '', start=start)

        # Etapa segun antiguedad; los cerrados terminan en «Finalizado».
        age_months = (today.year - start.year) * 12 + today.month - start.month
        case['stage'] = min(5, age_months // 10)
        if i % 6 == 5:
            case.update(active=False, stage=5)
        if i % 11 == 10:
            case['dash'] = False
        instances = choices.instances_for(service)
        case['instance'] = instances[min(case['stage'], len(instances) - 1)]

        if extra == 'admin':
            case.update(sector='Público', entity=f'Entidad Pública Demo {i}',
                        administrative_case_number=f'ADM-{start.year}-{1000 + i}',
                        administrative_city=CITIES[i % len(CITIES)])
        elif extra:
            case.update(court=extra, city=CITIES[i % len(CITIES)],
                        case_number=f'{start.year}-{2000 + i * 13:05d}-00')

        if i % 7 == 6:
            case['mandate'] = M.PRO_BONO if i % 2 == 0 else M.GUARDIANSHIP
        elif i % 5 == 2:
            value = (8 + i * 3) * MILLION
            state = (i // 5) % 3
            case.update(mandate=M.CONTINGENCY, pct=0, value=value,
                        paid=(0, (value // 2) // 100_000 * 100_000, value)[state])
            case['paz'] = state == 2 and i % 2 == 0
        elif i % 5 == 4:
            case.update(mandate=M.CONTINGENCY, pct=(10, 20, 30, 40, 50)[(i // 5) % 5],
                        value=(40 + i * 17) * MILLION)
        else:
            case.update(mandate=M.PAYMENT, **payment_plan(i, start, today))
            paid_in_full = (case['fee'] == sum(
                row['amount'] for row in case['history'] if row['kind'] != 'expected'))
            case['paz'] = paid_in_full and i % 2 == 0

        notes = []
        when = start + timedelta(days=20)
        when = min(when, today)
        if i % 3 == 0:
            notes.append(N(K.INFO, 'Novedad del proceso',
                           'Se presentó el escrito y estamos pendientes de respuesta.',
                           when, notified=i % 2 == 0))
        if i % 6 == 0:
            notes.append(N(K.DOCUMENT, 'Documento pendiente',
                           'Envíenos el documento solicitado para continuar.',
                           when, notified=True))
        if i % 8 == 0:
            notes.append(N(K.BLOCKED, 'Entidad sin respuesta',
                           'La entidad no ha respondido; seguimos insistiendo.',
                           when))
        if i % 10 == 0:
            notes.append(N(K.STAGE, 'Cambio de etapa',
                           'El asunto avanzó de etapa.', when))
        case['notes'] = notes

        clients.append(dict(
            n=100 + i,
            name=f'{FIRST_NAMES[i]} {SURNAMES[i % 12]} {SURNAMES[(i + 7) % 12]}',
            email=None if i % 4 == 3 else f'cliente{100 + i}@example.com',
            phone=None if i % 6 == 1 else f'30055502{i:02d}',
            active=i % 9 != 8,
            cases=[case],
        ))
    return clients


def payment_plan(i, start, today):
    """Honorarios en n cuotas: las vencidas se pagan, las futuras se programan."""
    installments = 2 + i % 4
    agreed = (6 + (i * 13) % 85) * MILLION
    unit = (agreed // installments) // 100_000 * 100_000
    parts = [unit] * (installments - 1) + [agreed - unit * (installments - 1)]
    history = []
    for index, amount in enumerate(parts):
        if index == 0:
            history.append(A(amount, start))
            continue
        if i % 4 == 0 and index == len(parts) - 1:
            continue  # ultima cuota sin programar: saldo por cobrar sin fecha
        when = start + timedelta(days=15 + 75 * (index - 1))
        history.append(P(amount, when) if when <= today else E(amount, when))
    return {'fee': agreed, 'history': history}


# ---------------------------------------------------------------------------
# El comando
# ---------------------------------------------------------------------------

def at(value):
    return timezone.make_aware(datetime.combine(value, time(9, 0)))


CASE_FIELDS = (
    'service', 'procedure', 'area', 'subtype', 'second_subtype', 'stage',
    'instance', 'case_number', 'court', 'city', 'sector', 'entity',
    'administrative_case_number', 'administrative_city', 'police_instance',
    'police_office', 'police_case_number', 'police_city', 'service_other',
    'procedure_other', 'area_other', 'subtype_other', 'second_subtype_other',
)


class Command(BaseCommand):
    help = ('Crea clientes, asuntos, finanzas y notas de demostracion para el '
            'gestor. Idempotente y sin borrar nada.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--user', metavar='USERNAME',
            help='Añade a ese usuario al grupo del gestor (no toca nada mas).',
        )

    def handle(self, *args, **options):
        username = options.get('user')
        user = None
        if username:
            User = get_user_model()
            user = User._default_manager.filter(
                **{User.USERNAME_FIELD: username}).first()
            if user is None:
                raise CommandError(f'No existe el usuario "{username}".')

        today = timezone.localdate()
        created = skipped = 0
        specs = [*handmade_clients(), *generated_clients(today),
                 *document_clients()]
        for spec in specs:
            identification = spec.get('identification') or (
                f'{PREFIX}{spec["n"]:06d}')
            if ClientModel.all_objects.filter(identification=identification).exists():
                skipped += 1
                continue
            with transaction.atomic():
                self._create_client(identification, spec)
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'{created} clientes creados, {skipped} ya existian.'))

        if user is not None:
            call_command('setup_case_manager_group', stdout=self.stdout)
            group = Group.objects.get(name=GESTOR_GROUP)
            user.groups.add(group)  # solo añade; no toca contrasena ni atributos
            self.stdout.write(self.style.SUCCESS(
                f'"{username}" pertenece al grupo "{GESTOR_GROUP}".'))

    def _create_client(self, identification, spec):
        first_start = min(c['start'] for c in spec['cases'])
        id_type = spec.get('id_type', 'CC')
        rep = spec.get('legal_rep') or {}
        client = ClientModel(
            identification_type=id_type,
            identification=identification,
            verification_digit=(
                nit_check_digit(identification) if id_type == 'NIT' else ''),
            full_name=spec['name'],
            email=spec['email'], phone=spec['phone'],
            legal_rep_name=rep.get('name', ''),
            legal_rep_identification_type=rep.get('id_type', ''),
            legal_rep_identification=rep.get('identification', ''),
            legal_rep_email=rep.get('email', ''),
            legal_rep_phone=rep.get('phone', ''),
            is_active=spec.get('active', True), created=at(first_start))
        client.full_clean()
        client.save()

        for data in spec['cases']:
            self._create_case(client, data)

    def _create_case(self, client, data):
        case = CaseModel(
            client=client, is_active=data.get('active', True),
            paz_y_salvo_authorized=data.get('paz', False),
            created=at(data['start']),
            **{f: data[f] for f in CASE_FIELDS if data.get(f) not in (None, '')})
        case.full_clean()
        case.save()

        history = data.get('history', [])
        mandate = data['mandate']
        agreed = data.get('fee', 0)
        paid = data.get('paid', 0)
        if mandate == M.PAYMENT:
            paid = sum(r['amount'] for r in history if r['kind'] != 'expected')
            if paid > agreed:
                raise CommandError(
                    f'Datos incoherentes en {client.identification}: '
                    f'abonos {paid} > honorarios {agreed}.')
        finance = CaseFinanceModel(
            case=case, start_date=data['start'], mandate=mandate,
            contingency_percentage=data.get('pct', 0),
            contingency_value=data.get('value', 0),
            agreed_fee=agreed, paid_amount=paid, payment_history=history,
            show_in_dashboard=data.get('dash', True), created=at(data['start']))
        finance.full_clean()
        finance.save()

        for note in data.get('notes', []):
            row = CaseNoteModel(
                case=case, kind=note['kind'], title=note['title'],
                body=note['body'], visible_to_client=note['visible'],
                notified_at=at(note['when']) if note['notified'] else None,
                created=at(note['when']))
            row.full_clean()
            row.save()

"""
El vocabulario del gestor: servicios, tramites, areas, subtipos y etapas.

Todo esto vivia como constantes de JavaScript dentro de
``apps/common/core/templates/pages/consultar_proceso.html`` --``SUBSERVICIOS``,
``SUBTIPOS``, ``ETAPAS_V35`` y el array ``E``--, que es donde lo aprobo el
cliente. Aqui esta el mismo arbol, palabra por palabra, en un solo sitio del
que tiran el modelo, los formularios y el admin.

Que este en Python y no en la plantilla importa por una razon concreta: en el
navegador una lista de opciones es una sugerencia --se edita el ``<select>`` y
se manda lo que sea--, y en el servidor es una restriccion. Las que aqui son
``choices`` las valida Django en cada ``full_clean()``.

Los dos arboles que dependen de otro campo (subtipo segun area, etapa segun
servicio) **no** se pueden expresar como ``choices`` de Django, que no conoce
mas que un campo. Se validan en ``CaseModel.clean()``.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Service(models.TextChoices):
    """Servicio contratado. El ``<select id="as">`` de la pantalla aprobada."""

    ADMINISTRATIVE = 'Administrativo', _('Administrativo')
    JUDICIAL = 'Representación judicial', _('Representación judicial')
    CONCILIATION = 'Conciliación', _('Conciliación')
    CONSULTING = 'Consultoría', _('Consultoría')
    FIELD_RESEARCH = 'Investigación de campo', _('Investigación de campo')
    OTHER = 'Otro', _('Otro')


class Procedure(models.TextChoices):
    """Tipo de tramite. El ``<select id="at">``; decide que bloque se pide."""

    ADMINISTRATIVE = 'Administrativo', _('Administrativo')
    PRIVATE = 'Privado', _('Privado')
    TUTELA = 'Acción de tutela', _('Acción de tutela')
    ORDINARY = 'Proceso ordinario', _('Proceso ordinario')
    EXECUTIVE = 'Proceso ejecutivo', _('Proceso ejecutivo')
    CONCILIATION = 'Conciliación', _('Conciliación')
    FIELD_RESEARCH = 'Investigación de campo', _('Investigación de campo')
    NOTARIAL = 'Trámite notarial', _('Trámite notarial')
    REGISTRY = 'Trámite registral', _('Trámite registral')
    POLICE = 'Querella policiva', _('Querella policiva')
    OTHER = 'Otro', _('Otro')


class Area(models.TextChoices):
    """Area o tipo de caso. El ``<select id="aa">``."""

    PENSION = 'Pensional / Seguridad Social', _('Pensional / Seguridad Social')
    LABOR = 'Laboral', _('Laboral')
    CIVIL = 'Civil', _('Civil')
    FAMILY = 'Familia', _('Familia')
    INHERITANCE = 'Sucesiones', _('Sucesiones')
    ADMINISTRATIVE = 'Administrativo', _('Administrativo')
    INSURANCE = 'Seguros', _('Seguros')
    INSOLVENCY = 'Insolvencia', _('Insolvencia')
    CONCILIATION = 'Conciliación', _('Conciliación')
    CRIMINAL = 'Penal', _('Penal')
    CONSUMER = 'Consumidor', _('Consumidor')
    COMMERCIAL = 'Comercial / Empresarial', _('Comercial / Empresarial')
    FIELD_RESEARCH = 'Investigación de campo', _('Investigación de campo')
    OTHER = 'Otro', _('Otro')


class Court(models.TextChoices):
    """Despacho o autoridad judicial. Solo en `Proceso ordinario`."""

    MUNICIPAL = 'Juzgado Municipal', _('Juzgado Municipal')
    CIRCUIT = 'Juzgado del Circuito', _('Juzgado del Circuito')
    SUPERIOR = 'Tribunal Superior', _('Tribunal Superior')
    SUPREME = 'Corte Suprema de Justicia', _('Corte Suprema de Justicia')
    STATE_COUNCIL = 'Consejo de Estado', _('Consejo de Estado')
    CONSTITUTIONAL = 'Corte Constitucional', _('Corte Constitucional')
    SUPERINTENDENCE = 'Superintendencia', _('Superintendencia')


class Sector(models.TextChoices):
    """Naturaleza del tramite. Solo en `Administrativo`."""

    PUBLIC = 'Público', _('Público')
    PRIVATE = 'Privado', _('Privado')


class PoliceInstance(models.TextChoices):
    """Instancia de la querella policiva."""

    FIRST = 'Primera instancia', _('Primera instancia')
    SECOND = 'Segunda instancia', _('Segunda instancia')


class Mandate(models.TextChoices):
    """
    Modalidad del contrato. Es el campo del que cuelga todo el dinero.

    Cual de los cuatro sea decide que columnas tienen sentido y como suma el
    caso en el panel: ver ``CaseFinanceModel``.
    """

    CONTINGENCY = 'Cuota litis', _('Cuota litis')
    PAYMENT = 'Modalidad de pago', _('Modalidad de pago')
    PRO_BONO = 'Ad honorem', _('Ad honorem')
    GUARDIANSHIP = 'Curaduría', _('Curaduría')


class NoteKind(models.TextChoices):
    """
    De que va una nota del expediente.

    No es decoracion: decide el color y el icono con que la ve el cliente en
    el portal, y el asunto del correo si se le avisa. Un «falta un documento»
    pintado igual que un «seguimos trabajando» se lee igual, y el cliente no
    manda el documento.
    """

    #: Novedad sin mas. La que no pide nada al cliente.
    INFO = 'INFO', _('Update')

    #: El asunto no avanza y la razon no depende del cliente --un juzgado que
    #: no responde, una entidad que no resuelve--. Se le cuenta para que no
    #: interprete el silencio.
    BLOCKED = 'BLOCKED', _('On hold')

    #: Hace falta algo suyo. Es la unica que le pide una accion, y por eso se
    #: distingue de las demas a simple vista.
    DOCUMENT = 'DOCUMENT', _('Document required')

    #: La escribe el sistema cuando cambia la etapa, no una persona.
    STAGE = 'STAGE', _('Stage change')


#: Como se pinta cada tipo de nota. La clase de Bootstrap y el icono van
#: juntos a proposito: el color solo no distingue --el ambar de «en espera» y
#: el rojo de «falta un documento» se parecen con una deficiencia de vision
#: del color-- y el icono tampoco basta. Van los dos, mas el texto del tipo.
NOTE_STYLES: dict[str, dict[str, str]] = {
    'INFO': {'tone': 'info', 'icon': 'info-circle'},
    'BLOCKED': {'tone': 'warning', 'icon': 'pause-circle'},
    'DOCUMENT': {'tone': 'danger', 'icon': 'file-earmark-arrow-up'},
    'STAGE': {'tone': 'success', 'icon': 'arrow-right-circle'},
}


class Stage(models.IntegerChoices):
    """
    El avance publico del caso: la barra de progreso de la pantalla aprobada.

    Es **un entero y no un texto** porque el orden es la mitad de su
    significado: la barra pinta como hechas las etapas menores que la actual.
    Son el array ``E`` del JavaScript, en su orden, y ese orden no se toca sin
    mirar la barra.
    """

    DOCUMENTS_RECEIVED = 0, _('Documentos recibidos')
    UNDER_REVIEW = 1, _('En estudio')
    IN_PROGRESS = 2, _('En trámite')
    IN_DEVELOPMENT = 3, _('En desarrollo')
    FINAL_STAGE = 4, _('Etapa final')
    FINISHED = 5, _('Finalizado')


#: Subtipo segun el area (``SUBTIPOS`` del JavaScript).
#:
#: Django no sabe validar un campo contra el valor de otro, asi que esto no
#: puede ser `choices`: lo comprueba ``CaseModel.clean()``.
SUBTYPES_BY_AREA: dict[str, tuple[str, ...]] = {
    Area.PENSION: (
        'Pensión integral de vejez',
        'Pensión de invalidez',
        'Pensión de sobrevivientes / sustitución pensional',
        'Pilar semicontributivo – renta vitalicia',
        'Prestación anticipada de vejez',
        'Pensión familiar',
        'Calificación de pérdida de capacidad laboral',
        'Reliquidación pensional',
        'Indemnización sustitutiva / devolución de saldos – cuando proceda',
        'Cálculo pensional',
        'Cálculo actuarial',
        'Corrección de historia laboral',
        'Otro trámite pensional',
    ),
    Area.LABOR: (
        'Contrato de trabajo',
        'Despido / terminación',
        'Reintegro / estabilidad laboral reforzada',
        'Acreencias laborales',
        'Seguridad social',
        'Accidente de trabajo / enfermedad laboral',
        'Proceso ordinario laboral',
        'Proceso ejecutivo laboral',
        'Otro laboral',
    ),
    Area.CIVIL: (
        'Responsabilidad civil',
        'Contratos',
        'Incumplimiento contractual',
        'Pertenencia',
        'Posesorio',
        'Servidumbres',
        'Proceso ejecutivo',
        'Proceso declarativo',
        'Bienes / propiedad',
        'Otro civil',
    ),
    Area.FAMILY: (
        'Divorcio',
        'Alimentos',
        'Custodia y cuidado personal',
        'Regulación de visitas',
        'Unión marital de hecho',
        'Liquidación de sociedad conyugal / patrimonial',
        'Filiación',
        'Otro de familia',
    ),
    Area.INHERITANCE: (
        'Sucesión intestada',
        'Sucesión testada',
        'Liquidación notarial',
        'Liquidación judicial',
        'Partición / adjudicación',
        'Otro sucesoral',
    ),
    Area.ADMINISTRATIVE: (
        'Petición / actuación administrativa',
        'Recurso administrativo',
        'Medio de control',
        'Responsabilidad del Estado',
        'Trámite ante entidad pública',
        'Otro administrativo',
    ),
    Area.INSURANCE: (
        'Reclamación de seguro',
        'Objeción de aseguradora',
        'Seguro de vida',
        'Seguro de cumplimiento',
        'Responsabilidad civil',
        'ARL',
        'Otro de seguros',
    ),
    Area.INSOLVENCY: (
        'Persona natural no comerciante',
        'Persona natural comerciante',
        'Reorganización empresarial',
        'Liquidación patrimonial',
        'Negociación de deudas',
        'Convalidación de acuerdo',
        'Otro de insolvencia',
    ),
    Area.CONCILIATION: (
        'Laboral',
        'Civil',
        'Familia',
        'Deudas',
        'Comercial',
        'Consumidor',
        'Administrativa',
        'Otra conciliación',
    ),
    Area.CRIMINAL: (
        'Denuncia / querella',
        'Defensa penal',
        'Representación de víctima',
        'Audiencias / proceso penal',
        'Otro penal',
    ),
    Area.CONSUMER: (
        'Protección al consumidor',
        'Garantía / calidad',
        'Incumplimiento contractual',
        'Servicios financieros',
        'Otro consumidor',
    ),
    Area.COMMERCIAL: (
        'Societario',
        'Contratos comerciales',
        'Cobro / cartera',
        'Conflicto societario',
        'Reorganización',
        'Otro comercial',
    ),
    Area.FIELD_RESEARCH: (
        'Verificación documental',
        'Verificación de bienes',
        'Visita / inspección',
        'Localización / constatación',
        'Otra investigación',
    ),
    Area.OTHER: ('Otro',),
}

#: Subnivel segun el servicio (``SUBSERVICIOS`` del JavaScript). Los servicios
#: que no estan aqui toman su subtipo del area, via `SUBTYPES_BY_AREA`.
SUBTYPES_BY_SERVICE: dict[str, tuple[str, ...]] = {
    Service.ADMINISTRATIVE: (
        'PQR / Derecho de petición',
        'Recurso de reposición',
        'Recurso de insistencia',
        'Acción de tutela',
    ),
    Service.CONSULTING: (
        'Consultoría procesal',
        'Consultoría empresarial',
    ),
    Service.FIELD_RESEARCH: (
        'Investigación judicial',
        'Estudio de seguridad',
    ),
    Service.JUDICIAL: (),
    Service.CONCILIATION: (),
    Service.OTHER: (),
}

#: Etapa o instancia segun el servicio (``ETAPAS_V35`` del JavaScript). Es
#: distinta de `Stage`: `Stage` es el avance publico, esto es donde va el
#: expediente dentro de su propio tramite.
INSTANCES_BY_SERVICE: dict[str, tuple[str, ...]] = {
    Service.JUDICIAL: (
        'Primera instancia',
        'Segunda instancia',
        'Casación',
        'Ejecución',
    ),
    Service.ADMINISTRATIVE: (
        'Etapa inicial',
        'Recurso',
        'Decisión definitiva',
    ),
    Service.CONCILIATION: (
        'Solicitud presentada',
        'Audiencia programada',
        'En negociación',
        'Finalizada',
    ),
    Service.CONSULTING: (
        'En estudio',
        'En elaboración',
        'Entregada',
        'Finalizada',
    ),
    Service.FIELD_RESEARCH: (
        'Asignada',
        'En investigación',
        'Informe en elaboración',
        'Informe entregado',
        'Finalizada',
    ),
    Service.OTHER: (
        'Inicial',
        'En trámite',
        'En desarrollo',
        'Etapa final',
        'Finalizado',
    ),
}

#: Lo que el formulario deja escribir a mano cuando nada de la lista encaja.
OTHER = 'Otro'

#: Porcentajes de cuota litis que ofrece la pantalla aprobada. El 0 no es
#: "ninguno": es **valor fijo cerrado**, y cuenta como deuda y no como
#: expectativa. Ver `CaseFinanceModel`.
CONTINGENCY_PERCENTAGES = (0, 10, 20, 30, 40, 50)


def subtypes_for(service: str, area: str) -> tuple[str, ...]:
    """
    Los subtipos validos para un servicio y un area.

    Reproduce la regla de la pantalla: `Representación judicial` y
    `Conciliación` sacan el subtipo del **area**; los demas servicios lo sacan
    del **servicio**. Cuando el servicio no ofrece ninguno, cualquier texto
    vale y devuelve la tupla vacia.
    """
    if service not in (Service.JUDICIAL, Service.CONCILIATION):
        return SUBTYPES_BY_SERVICE.get(service, ())

    subtypes = SUBTYPES_BY_AREA.get(area, ())
    if not subtypes:
        return ()
    # La pantalla anade siempre `Otro` al final si el area no lo trae ya.
    return subtypes if OTHER in subtypes else subtypes + (OTHER,)


def instances_for(service: str) -> tuple[str, ...]:
    """Las etapas o instancias validas para un servicio."""
    return INSTANCES_BY_SERVICE.get(service, ())

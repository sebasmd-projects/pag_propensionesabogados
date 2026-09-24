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
    CONCILIATION = 'Conciliación', _('Conciliación')
    CONSULTING = 'Consultoría', _('Consultoría')
    FIELD_RESEARCH = 'Investigación de campo', _('Investigación de campo')
    JUDICIAL = 'Representación judicial', _('Representación judicial')
    OTHER = 'Otro', _('Otro')


class Procedure(models.TextChoices):
    """Tipo de tramite. El ``<select id="at">``; decide que bloque se pide."""

    TUTELA = 'Acción de tutela', _('Acción de tutela')
    ADMINISTRATIVE = 'Administrativo', _('Administrativo')
    CONCILIATION = 'Conciliación', _('Conciliación')
    FIELD_RESEARCH = 'Investigación de campo', _('Investigación de campo')
    PRIVATE = 'Privado', _('Privado')
    EXECUTIVE = 'Proceso ejecutivo', _('Proceso ejecutivo')
    ORDINARY = 'Proceso ordinario', _('Proceso ordinario')
    POLICE = 'Querella policiva', _('Querella policiva')
    NOTARIAL = 'Trámite notarial', _('Trámite notarial')
    REGISTRY = 'Trámite registral', _('Trámite registral')
    OTHER = 'Otro', _('Otro')


class Area(models.TextChoices):
    """Area o tipo de caso. El ``<select id="aa">``."""

    ADMINISTRATIVE = 'Administrativo', _('Administrativo')
    CIVIL = 'Civil', _('Civil')
    COMMERCIAL = 'Comercial / Empresarial', _('Comercial / Empresarial')
    CONCILIATION = 'Conciliación', _('Conciliación')
    CONSUMER = 'Consumidor', _('Consumidor')
    FAMILY = 'Familia', _('Familia')
    INSOLVENCY = 'Insolvencia', _('Insolvencia')
    FIELD_RESEARCH = 'Investigación de campo', _('Investigación de campo')
    LABOR = 'Laboral', _('Laboral')
    CRIMINAL = 'Penal', _('Penal')
    PENSION = 'Pensional / Seguridad Social', _('Pensional / Seguridad Social')
    INSURANCE = 'Seguros', _('Seguros')
    INHERITANCE = 'Sucesiones', _('Sucesiones')
    OTHER = 'Otro', _('Otro')


class Court(models.TextChoices):
    """
    Despacho o autoridad judicial. Solo en `Representación judicial`.

    La lista aprobada saltaba de `Juzgado del Circuito` al `Consejo de Estado`
    y dejaba fuera las dos primeras instancias de lo contencioso
    administrativo, que son justamente donde se radica un medio de control:
    sin ellas, una nulidad y restablecimiento del derecho no tenia despacho
    que escoger. Estan `JUDGE_ADMIN` y `TRIBUNAL_ADMIN`.
    """

    STATE_COUNCIL = 'Consejo de Estado', _('Consejo de Estado')
    CONSTITUTIONAL = 'Corte Constitucional', _('Corte Constitucional')
    SUPREME = 'Corte Suprema de Justicia', _('Corte Suprema de Justicia')
    JUDGE_ADMIN = 'Juzgado Administrativo', _('Juzgado Administrativo')
    CIRCUIT = 'Juzgado del Circuito', _('Juzgado del Circuito')
    MUNICIPAL = 'Juzgado Municipal', _('Juzgado Municipal')
    SUPERINTENDENCE = 'Superintendencia', _('Superintendencia')
    TRIBUNAL_ADMIN = 'Tribunal Administrativo', _('Tribunal Administrativo')
    SUPERIOR = 'Tribunal Superior', _('Tribunal Superior')


class Sector(models.TextChoices):
    """Naturaleza del tramite. Solo en `Administrativo`."""

    PRIVATE = 'Privado', _('Privado')
    PUBLIC = 'Público', _('Público')


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

    PRO_BONO = 'Ad honorem', _('Ad honorem')
    CONTINGENCY = 'Cuota litis', _('Cuota litis')
    GUARDIANSHIP = 'Curaduría', _('Curaduría')
    PAYMENT = 'Modalidad de pago', _('Modalidad de pago')


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


#: Subtipo segun el area: el ``SUBTIPOS`` del JavaScript **anterior**.
#:
#: Ya no alimenta ningun desplegable --la cadena aprobada es servicio ->
#: subtipo -> segundo subnivel, sin area por medio--. Se conserva por una
#: sola razon: los expedientes que ya estan guardados se clasificaron con
#: estas listas, y borrarlas haria que al abrir uno de ellos el formulario
#: rechazara su propio subtipo. Se aceptan al validar; no se ofrecen al
#: clasificar de nuevo.
LEGACY_SUBTYPES_BY_AREA: dict[str, tuple[str, ...]] = {
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

#: El arbol de clasificacion, tal y como quedo en el HTML aprobado
#: (``ARBOL41``: «CONTROL ÚNICO DE SERVICIO / ÁREA / TIPO DE PROCESO»).
#:
#: Tiene tres niveles y **solo** tres: servicio -> subtipo -> segundo
#: subnivel. En `Representación judicial` el segundo nivel se rotula «Área» y
#: el tercero «Tipo concreto de proceso» --eso es lo que quiere decir
#: «representación judicial > penal > tipo de proceso»--; en los demas
#: servicios el segundo nivel es el subnivel y no hay tercero.
#:
#: Que el arbol este completo aqui es lo que permite que cada desplegable
#: cargue **solo** lo que cuelga de la rama elegida. Antes el subtipo judicial
#: mezclaba las jurisdicciones con los subtipos de todas las areas, y por eso
#: un expediente correcto podia recibir «este subtipo no corresponde».
CLASSIFICATION_TREE: dict[str, dict[str, tuple[str, ...]]] = {
    Service.ADMINISTRATIVE: {
        'PQR / Derecho de petición': (),
        'Recurso de reposición': (),
        'Recurso de insistencia': (),
        'Acción de tutela': (),
    },
    Service.CONCILIATION: {
        'Conciliación privada': (),
        'Centro de conciliación': (),
        'Conciliación judicial': (),
        'Comisaría de Familia': (),
        'Inspección de Policía': (),
    },
    Service.CONSULTING: {
        'Consultoría procesal': (),
        'Consultoría empresarial': (),
    },
    Service.FIELD_RESEARCH: {
        'Investigación judicial': (),
        'Estudio de seguridad': (),
    },
    Service.JUDICIAL: {
        'Civil': (
            'Ejecutivo',
            'Monitorio',
            'Pertenencia / prescripción adquisitiva',
            'Reivindicatorio',
            'Restitución de inmueble',
            'Divisorio',
            'Deslinde y amojonamiento',
            'Servidumbre',
            'Responsabilidad civil',
            'Incumplimiento contractual',
            'Promesa de compraventa',
        ),
        'Laboral': (
            'Ordinario laboral',
            'Ejecutivo laboral',
            'Contrato realidad',
            'Reintegro / estabilidad laboral reforzada',
            'Fuero sindical',
            'Acreencias laborales',
            'Pensión de vejez',
            'Pensión de invalidez',
            'Pensión de sobrevivientes',
            'Reliquidación pensional',
            'Calificación / pérdida de capacidad laboral',
        ),
        'Familia': (
            'Divorcio / cesación de efectos civiles',
            'Unión marital de hecho',
            'Liquidación de sociedad conyugal o patrimonial',
            'Alimentos',
            'Ejecutivo de alimentos',
            'Custodia y cuidado personal',
            'Regulación de visitas',
            'Filiación',
            'Investigación de paternidad',
            'Impugnación de paternidad',
            'Sucesión',
            'Petición de herencia',
        ),
        'Penal': (
            'Defensa penal',
            'Representación de víctimas',
            'Denuncia penal',
            'Querella penal',
            'Incidente de reparación integral',
            'Ejecución de penas',
        ),
        'Contencioso administrativo': (
            'Nulidad',
            'Nulidad y restablecimiento del derecho',
            'Reparación directa',
            'Controversias contractuales',
            'Ejecutivo administrativo',
            'Cumplimiento',
            'Repetición',
        ),
        'Superintendencias': (
            'Protección al consumidor',
            'Protección al consumidor financiero',
            'Asuntos societarios',
            'Competencia desleal',
            'Propiedad industrial',
        ),
    },
    Service.OTHER: {},
}

#: Etapa o instancia segun el servicio (``ETAPAS_V35`` del JavaScript). Es
#: distinta de `Stage`: `Stage` es el avance publico, esto es donde va el
#: expediente dentro de su propio tramite.
#:
#: **No** se ordena alfabeticamente, y es la unica lista que no: igual que
#: `Stage`, el orden *es* la mitad del significado --una casacion va despues
#: de una segunda instancia, no entre «Casación» y «Ejecución»--.
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

#: Equivalencias para ordenar sin que las tildes manden al final lo que
#: empieza por vocal acentuada. `sorted()` compara puntos de codigo, y en
#: Unicode la «ó» va despues de la «z»: sin esto, «Acción de tutela» quedaria
#: detras de «Trámite registral».
_SIN_TILDE = str.maketrans('áàäâéèëêíìïîóòöôúùüûñ', 'aaaaeeeeiiiioooouuuun')


def alphabetical(values) -> tuple[str, ...]:
    """
    Los valores en orden alfabetico, con los «Otro…» al final.

    Un desplegable largo se lee buscando, y buscar en una lista que no esta
    ordenada es recorrerla entera. Lo unico que no se ordena es el comodin:
    «Otro» es la salida de emergencia y su sitio es el ultimo, no el que le
    toque por la o.
    """
    sin_duplicados = tuple(dict.fromkeys(v for v in values if v))
    return tuple(sorted(
        sin_duplicados,
        key=lambda v: (is_other(v), v.translate(_SIN_TILDE).casefold()),
    ))


def is_other(value: str) -> bool:
    return (value or '').lower().startswith(('otro', 'otra'))


def subtypes_for(service: str, area: str = '') -> tuple[str, ...]:
    """
    Los subtipos que cuelgan del servicio, y nada mas.

    `area` ya no decide nada --el arbol aprobado la dejo fuera de la cadena--,
    pero se sigue recibiendo para aceptar los subtipos de expedientes
    anteriores, que si se clasificaron por area. Un expediente viejo se puede
    volver a guardar sin que el formulario le cambie la clasificacion por su
    cuenta.
    """
    values = tuple(CLASSIFICATION_TREE.get(service, {}))
    if not values:
        return (OTHER,) if service else ()
    legacy = LEGACY_SUBTYPES_BY_AREA.get(area, ()) if area else ()
    return (*alphabetical((*values, *legacy)), OTHER)


def second_subtypes_for(service: str, subtype: str) -> tuple[str, ...]:
    """
    El tercer nivel, si esa rama tiene uno.

    Devuelve vacio cuando no lo tiene --un «Recurso de reposición» no se
    subdivide--, y eso es lo que le dice al formulario que esconda el campo en
    vez de ensenarlo con un unico «Otro» dentro.
    """
    branch = CLASSIFICATION_TREE.get(service, {}).get(subtype, ())
    return (*alphabetical(branch), OTHER) if branch else ()


def instances_for(service: str) -> tuple[str, ...]:
    """Las etapas o instancias validas para un servicio."""
    return INSTANCES_BY_SERVICE.get(service, ())

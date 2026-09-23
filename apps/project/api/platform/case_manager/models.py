"""
Gestor de procesos y clientes: clientes, procesos y su informacion financiera.

Sustituye al almacen que hasta ahora vivia en `localStorage.propDemo`, dentro
de `apps/common/core/templates/pages/consultar_proceso.html`. Alli un
expediente era una entrada de un objeto JSON con claves de dos letras (`n`,
`s`, `hp`, `ge`, `pl`, `vl`...), el navegador de cualquier visitante recibia
**todos** los expedientes, y borrar la cache del navegador borraba el despacho.

Tres cosas que conviene entender antes de tocar nada:

1. **El saldo no es una columna.** Se calcula (`CaseFinanceModel.balance`).
   Guardarlo seria guardar dos veces el mismo hecho y abrir la puerta a que
   no coincidan; el historico de pagos, que si justificaria guardarlo, esta
   fuera del alcance contratado.

2. **Deudores y expectativas de cobro no son tablas.** Son dos preguntas
   distintas sobre `CaseFinanceModel` --quien debe, y cuanto se espera ganar
   si el pleito sale-- y viven como consultas en `CaseFinanceQuerySet`. Son
   las dos listas del panel gerencial de la pantalla aprobada.

3. **`Cuota litis` con porcentaje 0 no es cuota litis.** Es un valor fijo
   cerrado: cuenta como deuda, no como expectativa. Es la regla mas facil de
   romper sin darse cuenta de todo el modulo, y por eso esta en
   `CaseFinanceModel.is_contingency_expectation` y no repartida por las
   vistas.
"""

import uuid

from auditlog.registry import auditlog
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q, Sum, Value
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from apps.common.utils.models import TimeStampedModel

from . import choices

#: Solo digitos: la identificacion se guarda normalizada, sin puntos ni
#: espacios, porque es la clave por la que pregunta el portal publico y
#: "16.484.186" y "16484186" tienen que ser la misma persona.
only_digits = RegexValidator(
    r'^\d+$',
    _('The identification must contain digits only.'),
)


class ClientModel(TimeStampedModel):
    """
    Una persona con uno o mas asuntos en el despacho.

    `is_active` es la **vigencia** del servicio, que es lo que el portal
    publico ensena como `ACTIVO` / `INACTIVO`: un cliente inactivo se
    identifica bien y aun asi no ve su expediente.
    """

    id = models.UUIDField(
        'ID',
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        serialize=False,
        editable=False
    )

    identification = models.CharField(
        _('identification'),
        max_length=20,
        unique=True,
        validators=[only_digits],
        help_text=_('Digits only, no dots or spaces.')
    )

    full_name = models.CharField(
        _('full name'),
        max_length=255
    )

    email = models.EmailField(
        _('email'),
        max_length=255,
        blank=True,
        null=True
    )

    phone = models.CharField(
        _('phone'),
        max_length=30,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        _('service in force'),
        default=True,
        help_text=_(
            'An inactive client identifies correctly but cannot see the case.'
        )
    )

    # -- El codigo de acceso al portal ------------------------------------
    #
    # Lo que habia antes era una clave **derivada**: la inicial del nombre mas
    # los cuatro ultimos digitos de la cedula. Eso no acredita a nadie. Son
    # diez mil combinaciones como mucho, se adivina con la cedula delante --que
    # es publica en media Colombia-- y no prueba que quien la teclea sea el
    # titular del proceso, que es justo lo que un expediente exige.
    #
    # Ahora el portal manda un codigo de seis cifras al correo registrado del
    # cliente. Quien lo recibe demuestra que controla ese buzon, que es el que
    # el despacho tiene anotado como suyo.
    #
    # Estos tres campos son la escalera de reenvios, y estan **en la base** y
    # no en la cache o la sesion a proposito: si vivieran en la sesion, tirar
    # la galleta la reiniciaria, y en cache con varios procesos cada uno
    # llevaria su cuenta. Lo que frena el envio de correos al buzon de un
    # tercero no puede depender de con que proceso le toque hablar.

    code_sends = models.PositiveSmallIntegerField(
        _('codes sent in the current cycle'),
        default=0,
        editable=False
    )

    last_code_sent_at = models.DateTimeField(
        _('last code sent at'),
        blank=True,
        null=True,
        editable=False
    )

    code_blocked_until = models.DateTimeField(
        _('codes blocked until'),
        blank=True,
        null=True,
        editable=False
    )

    @property
    def masked_email(self) -> str:
        """
        El correo con el centro tapado, para poder decir a donde fue el codigo.

        Sin esto la pantalla diria «te hemos mandado un codigo» y el cliente no
        sabria a cual de sus correos mirar --ni si el que el despacho tiene
        anotado sigue siendo el suyo, que es el fallo que mas llamadas genera--.

        Se tapa con un numero **fijo** de asteriscos y no con uno por letra: la
        longitud del nombre de un buzon tambien es informacion, y aqui no hace
        falta para nada.
        """
        correo = (self.email or '').strip()

        if '@' not in correo:
            return ''

        nombre, dominio = correo.rsplit('@', 1)

        if len(nombre) <= 4:
            # Un buzon corto no se puede tapar por el centro sin taparlo
            # entero: se deja la primera letra y ya.
            return f'{nombre[:1]}****@{dominio}'

        return f'{nombre[:3]}****{nombre[-3:]}@{dominio}'

    def save(self, *args, **kwargs):
        self.identification = ''.join(
            character
            for character in (self.identification or '')
            if character.isdigit()
        )
        self.full_name = ' '.join((self.full_name or '').split())
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.identification} - {self.full_name}'

    class Meta:
        db_table = 'apps_project_case_manager_client'
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['identification']),
        ]


class CaseQuerySet(models.QuerySet):
    def visible_to_client(self):
        """
        Lo que el portal publico puede llegar a ensenar.

        Un caso de un cliente sin vigencia no sale por aqui: la comprobacion
        va en el queryset y no en la plantilla, porque una plantilla que no
        pinta algo sigue habiendolo recibido.
        """
        return self.filter(is_active=True, client__is_active=True)


class CaseModel(TimeStampedModel):
    """
    Un asunto del despacho: el expediente que ve el cliente.

    Los tres bloques de campos del final --judicial, administrativo y
    policivo-- son excluyentes y dependen de `procedure`, igual que en la
    pantalla aprobada, donde `actualizarCampos()` ensena uno y esconde los
    otros dos. Lo que alli era esconder un `<div>`, aqui lo comprueba
    `clean()`.
    """

    id = models.UUIDField(
        'ID',
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        serialize=False,
        editable=False
    )

    client = models.ForeignKey(
        ClientModel,
        on_delete=models.CASCADE,
        related_name='cases',
        verbose_name=_('client')
    )

    service = models.CharField(
        _('contracted service'),
        max_length=50,
        choices=choices.Service.choices
    )

    procedure = models.CharField(
        _('procedure type'),
        max_length=50,
        choices=choices.Procedure.choices,
        blank=True,
        null=True
    )

    area = models.CharField(
        _('area / case type'),
        max_length=50,
        choices=choices.Area.choices,
        blank=True,
        null=True
    )

    subtype = models.CharField(
        _('subtype / speciality'),
        max_length=150,
        blank=True,
        null=True
    )

    second_subtype = models.CharField(
        _('second sublevel'),
        max_length=150,
        blank=True,
        null=True
    )

    stage = models.PositiveSmallIntegerField(
        _('stage'),
        choices=choices.Stage.choices,
        default=choices.Stage.DOCUMENTS_RECEIVED
    )

    instance = models.CharField(
        _('current stage / instance'),
        max_length=100,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        _('case in force'),
        default=True
    )

    # --- Bloque judicial: solo con `Proceso ordinario` ----------------------
    case_number = models.CharField(
        _('case number'),
        max_length=100,
        blank=True,
        null=True
    )

    court = models.CharField(
        _('court / judicial authority'),
        max_length=100,
        choices=choices.Court.choices,
        blank=True,
        null=True
    )

    city = models.CharField(
        _('city of the process'),
        max_length=100,
        blank=True,
        null=True
    )

    # --- Bloque administrativo: solo con `Administrativo` -------------------
    sector = models.CharField(
        _('nature of the procedure'),
        max_length=20,
        choices=choices.Sector.choices,
        blank=True,
        null=True
    )

    entity = models.CharField(
        _('entity / company'),
        max_length=255,
        blank=True,
        null=True
    )

    administrative_case_number = models.CharField(
        _('reference number'),
        max_length=100,
        blank=True,
        null=True
    )

    administrative_city = models.CharField(
        _('city of the procedure'),
        max_length=100,
        blank=True,
        null=True
    )

    # --- Bloque policivo: solo con `Querella policiva` ----------------------
    police_instance = models.CharField(
        _('police instance'),
        max_length=30,
        choices=choices.PoliceInstance.choices,
        blank=True,
        null=True
    )

    police_office = models.CharField(
        _('police inspection / authority'),
        max_length=255,
        blank=True,
        null=True
    )

    police_case_number = models.CharField(
        _('police case number'),
        max_length=100,
        blank=True,
        null=True
    )

    police_city = models.CharField(
        _('city / municipality'),
        max_length=100,
        blank=True,
        null=True
    )

    paz_y_salvo_authorized = models.BooleanField(
        _('paz y salvo authorized'),
        default=False,
        help_text=_(
            'The client can print the settlement letter only when the firm '
            'authorizes it here.'
        )
    )

    objects = CaseQuerySet.as_manager()

    @property
    def detail_rows(self) -> list[tuple[str, str]]:
        """
        Las filas del bloque de detalle, segun el tipo de tramite.

        Es `pintarDetalles()` del JavaScript, que armaba este mismo bloque
        concatenando HTML con `innerHTML`. Al devolver pares y dejar que la
        plantilla los pinte, el escapado de Django se aplica solo: un nombre
        de entidad con `<` deja de poder cerrar una etiqueta.

        Solo salen las filas con contenido, igual que antes.

        La instancia y el radicado **no estan aqui**: el diseno aprobado los
        subio a la rejilla de arriba, junto al nombre y al servicio, porque
        son lo que el cliente busca primero. Salen de `public_instance` y
        `public_reference`, que es lo mismo sin importar de que bloque venga
        cada asunto.
        """
        by_procedure = {
            choices.Procedure.ORDINARY: (
                (_('COURT'), self.court),
                (_('CITY OF THE PROCESS'), self.city),
            ),
            choices.Procedure.ADMINISTRATIVE: (
                (_('NATURE'), self.sector),
                (_('ENTITY / COMPANY'), self.entity),
                (_('CITY OF THE PROCEDURE'), self.administrative_city),
            ),
            choices.Procedure.POLICE: (
                (_('INSPECTION / AUTHORITY'), self.police_office),
                (_('CITY / MUNICIPALITY'), self.police_city),
            ),
        }
        rows = by_procedure.get(self.procedure, ())
        return [(label, value) for label, value in rows if value]

    @property
    def progress(self) -> list[dict]:
        """
        La barra de progreso: cada etapa con su estado respecto de la actual.

        El JavaScript la armaba recorriendo el array `E` y comparando indices.
        La comparacion es la misma; lo que cambia es que ahora la hace el
        servidor y la plantilla solo pinta.
        """
        return [
            {
                'number': value + 1,
                'label': label,
                'state': (
                    'done' if value < self.stage
                    else 'current' if value == self.stage
                    else ''
                ),
                'done': value < self.stage,
            }
            for value, label in choices.Stage.choices
        ]

    @property
    def paz_y_salvo_subject(self) -> str:
        """
        Como se nombra el asunto dentro del paz y salvo.

        Es `tipoProcesoPazYSalvoV77()` del JavaScript, con su regla intacta y
        su motivo escrito al lado en el original: **el paz y salvo no lleva
        numero de radicado**, solo identifica el tipo de tramite. Se toma lo
        mas concreto que haya, de dentro hacia fuera.
        """
        return (
            self.second_subtype
            or self.subtype
            or self.get_service_display()
            or _('legal service entrusted')
        )

    @property
    def public_reference(self) -> str:
        """
        El radicado que ensena el portal, venga del bloque que venga.

        En la pantalla aprobada esto era `d.r || d.ra || d.rp || "—"`.
        """
        return (
            self.case_number
            or self.administrative_case_number
            or self.police_case_number
            or '—'
        )

    @property
    def public_instance(self) -> str:
        """
        La etapa o instancia que ensena el portal, venga del bloque que venga.

        En la pantalla aprobada esto era `d.i || d.ip || "—"`: el asunto
        judicial guarda su instancia en `instance` y la querella policiva en
        `police_instance`, y el cliente no tiene por que saber cual de los dos
        bloques le toco.
        """
        return self.instance or self.police_instance or '—'

    @property
    def public_mandate(self) -> str:
        """
        La modalidad del contrato, tal y como se le ensena al cliente.

        Sale del bloque economico, que por lo demas no se asoma al portal:
        esta fila es la excepcion, y esta en la pantalla aprobada
        (`modCliente`). Con cuota litis se anade el porcentaje, porque «cuota
        litis» a secas no le dice a nadie cuanto va a pagar.

        Un asunto sin bloque economico devuelve la raya, no revienta: el
        bloque se rellena despues de dar de alta el asunto, y entre una cosa y
        otra el cliente ya puede estar consultando.
        """
        finance = getattr(self, 'finance', None)

        if finance is None or not finance.mandate:
            return '—'

        if (finance.mandate == choices.Mandate.CONTINGENCY
                and finance.contingency_percentage):
            return f'{finance.get_mandate_display()} ' \
                   f'({finance.contingency_percentage} %)'

        return finance.get_mandate_display()

    def clean(self):
        """
        Las reglas que en el navegador eran ensenar u ocultar un `<div>`.

        Esconder un campo no es validarlo: el `<select>` se edita y se manda
        lo que sea. Aqui se rechaza.
        """
        from django.core.exceptions import ValidationError

        errors = {}

        valid_subtypes = choices.subtypes_for(self.service, self.area)
        if self.subtype and valid_subtypes and self.subtype not in valid_subtypes:
            errors['subtype'] = _(
                'This subtype does not belong to the selected service and area.'
            )

        valid_instances = choices.instances_for(self.service)
        if self.instance and valid_instances and self.instance not in valid_instances:
            errors['instance'] = _(
                'This stage does not belong to the selected service.'
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f'{self.client.identification} - {self.service}'

    class Meta:
        db_table = 'apps_project_case_manager_case'
        verbose_name = _('Case')
        verbose_name_plural = _('Cases')
        ordering = ['-updated']
        indexes = [
            models.Index(fields=['client', '-updated']),
        ]


class CaseFinanceQuerySet(models.QuerySet):
    """
    Las preguntas del panel economico y del panel gerencial.

    Cada una vive aqui y no repartida por las vistas por la misma razon por la
    que `CaseModel.clean()` no vive en la plantilla: una regla que se repite
    en tres sitios acaba siendo tres reglas distintas.
    """

    def in_dashboard(self):
        """Los casos que el despacho decidio incluir en el panel economico."""
        return self.filter(show_in_dashboard=True, case__is_active=True)

    def debtors(self):
        """
        Quien debe dinero, hoy.

        Son dos cosas sumadas, y es la parte que mas se malentiende:
        `Modalidad de pago` con saldo, **y** `Cuota litis` al 0 %, que no es
        una expectativa sino un valor fijo cerrado que aun no se ha cobrado.
        """
        return self.in_dashboard().filter(
            Q(mandate=choices.Mandate.PAYMENT, agreed_fee__gt=F('paid_amount'))
            | Q(
                mandate=choices.Mandate.CONTINGENCY,
                contingency_percentage=0,
                contingency_value__gt=0,
            )
        )

    def expectations(self):
        """
        Lo que se espera ganar si los pleitos salen: `Cuota litis` sobre 0 %.

        No es dinero debido. Se ensena aparte **y ademas** se suma al
        pendiente potencial, tal como lo explica la propia pantalla.
        """
        return self.in_dashboard().filter(
            mandate=choices.Mandate.CONTINGENCY,
            contingency_percentage__gt=0,
            contingency_value__gt=0,
        )

    def totals(self) -> dict[str, int]:
        """
        Las cifras de cabecera del panel gerencial, en una sola consulta.

        Reproduce `actualizarPanelGerencial()` del JavaScript:

        - **pactado**: lo cerrado (`Modalidad de pago`, mas la cuota litis
          al 0 %, que es valor fijo).
        - **pagado**: lo que ya entro.
        - **saldo**: lo pactado que falta por cobrar.
        - **expectativa**: cuota litis sobre 0 %, que no es deuda.
        - **pendiente potencial** = saldo + expectativa.
        - **total proyectado** = pactado + expectativa.
        """
        zero = Value(0)
        rows = self.in_dashboard()

        payment = Q(mandate=choices.Mandate.PAYMENT)
        fixed = Q(mandate=choices.Mandate.CONTINGENCY, contingency_percentage=0)
        expectation = Q(
            mandate=choices.Mandate.CONTINGENCY, contingency_percentage__gt=0
        )

        aggregated = rows.aggregate(
            agreed_payment=Coalesce(
                Sum('agreed_fee', filter=payment), zero
            ),
            paid=Coalesce(Sum('paid_amount', filter=payment), zero),
            balance_payment=Coalesce(
                Sum(
                    Greatest(F('agreed_fee') - F('paid_amount'), zero),
                    filter=payment,
                ),
                zero,
            ),
            agreed_fixed=Coalesce(
                Sum('contingency_value', filter=fixed), zero
            ),
            expectation=Coalesce(
                Sum('contingency_value', filter=expectation), zero
            ),
        )

        agreed = aggregated['agreed_payment'] + aggregated['agreed_fixed']
        # La cuota litis fija esta cerrada y nada de ella se ha cobrado: entra
        # entera al saldo, igual que en la pantalla aprobada.
        balance = aggregated['balance_payment'] + aggregated['agreed_fixed']

        paid = aggregated['paid']
        expectation = aggregated['expectation']
        projected = agreed + expectation

        def share(value: int) -> float:
            """Que porcion del total proyectado es `value`, en tanto por cien."""
            return round(value * 100 / projected, 2) if projected else 0

        # Los tres tramos del anillo se miden sobre el **total proyectado**,
        # que es la suma de los tres: lo pagado, lo que falta por cobrar y la
        # expectativa. Es lo que hacia la pantalla aprobada, y no es lo mismo
        # que medir sobre lo pactado: un despacho con mucha cuota litis por
        # resolver tiene una tasa de recaudo baja aunque haya cobrado todo lo
        # cierto, y eso es precisamente lo que el anillo esta diciendo.
        #
        # El segundo tramo es **acumulado**: un `conic-gradient` no dibuja
        # anchos, dibuja cortes, asi que el corte de «por cobrar» va donde
        # termina, no donde empieza.
        return {
            'agreed': agreed,
            'paid': paid,
            'balance': balance,
            'expectation': expectation,
            'potential_pending': balance + expectation,
            'projected_total': projected,
            'collection_rate': round(share(paid)),
            'share_paid': share(paid),
            'share_balance': min(100, share(paid) + share(balance)),
        }

    def by_area(self) -> list[dict]:
        """
        Lo mismo, repartido por area, de mas a menos.

        Es la «Distribucion por area / tipo de caso» del panel aprobado, que
        el JavaScript armaba acumulando en un diccionario mientras recorria
        `localStorage`. Aqui es una consulta agrupada.

        Cada fila lleva `share`, el porcentaje que le toca del total
        proyectado, porque la barra se dibuja con el y calcularlo en la
        plantilla obligaria a un filtro de division que Django no trae.
        """
        zero = Value(0)

        payment = Q(mandate=choices.Mandate.PAYMENT)
        fixed = Q(mandate=choices.Mandate.CONTINGENCY, contingency_percentage=0)
        expectation = Q(
            mandate=choices.Mandate.CONTINGENCY, contingency_percentage__gt=0
        )

        rows = (
            self.in_dashboard()
            .values('case__area')
            .annotate(
                agreed_payment=Coalesce(
                    Sum('agreed_fee', filter=payment), zero
                ),
                agreed_fixed=Coalesce(
                    Sum('contingency_value', filter=fixed), zero
                ),
                expectation=Coalesce(
                    Sum('contingency_value', filter=expectation), zero
                ),
            )
        )

        areas = [
            {
                'area': row['case__area'] or _('No area recorded'),
                'total': (
                    row['agreed_payment']
                    + row['agreed_fixed']
                    + row['expectation']
                ),
            }
            for row in rows
        ]
        areas = [row for row in areas if row['total']]
        total = sum(row['total'] for row in areas)

        for row in areas:
            row['share'] = round(row['total'] * 100 / total) if total else 0

        return sorted(areas, key=lambda row: row['total'], reverse=True)


class CaseFinanceModel(TimeStampedModel):
    """
    El dinero de un caso: que se pacto, que entro y que falta.

    Va aparte de `CaseModel` a proposito. Son dos cosas con dos publicos: el
    expediente lo ve el cliente en el portal, y esto **no sale nunca de
    puertas adentro**. Separarlas hace que el serializador publico no pueda
    filtrar mal un campo que no tiene.

    Cuatro modalidades, y cada una usa columnas distintas:

    ===================  ==========================================
    `Modalidad de pago`  `agreed_fee` y `paid_amount`; debe la resta
    `Cuota litis` 0 %    `contingency_value`: valor fijo cerrado, se debe entero
    `Cuota litis` > 0 %  `contingency_value`: expectativa, no es deuda
    `Ad honorem`         nada; no hay dinero
    `Curaduría`          nada; no hay dinero
    ===================  ==========================================
    """

    id = models.UUIDField(
        'ID',
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        serialize=False,
        editable=False
    )

    case = models.OneToOneField(
        CaseModel,
        on_delete=models.CASCADE,
        related_name='finance',
        verbose_name=_('case')
    )

    start_date = models.DateField(
        _('start date'),
        blank=True,
        null=True,
        help_text=_('Month and year the matter started.')
    )

    mandate = models.CharField(
        _('contract modality'),
        max_length=30,
        choices=choices.Mandate.choices
    )

    contingency_percentage = models.PositiveSmallIntegerField(
        _('contingency percentage'),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('0 means a closed fixed value, not a contingency.')
    )

    contingency_value = models.PositiveBigIntegerField(
        _('contingency value'),
        default=0
    )

    agreed_fee = models.PositiveBigIntegerField(
        _('agreed fee'),
        default=0
    )

    paid_amount = models.PositiveBigIntegerField(
        _('paid amount'),
        default=0
    )

    show_in_dashboard = models.BooleanField(
        _('include in the financial dashboard'),
        default=True
    )

    objects = CaseFinanceQuerySet.as_manager()

    @property
    def is_contingency_expectation(self) -> bool:
        """
        Si esta fila es una **expectativa** y no una deuda.

        La regla que mas facil se rompe del modulo: `Cuota litis` al 0 % no es
        cuota litis, es un valor fijo cerrado.
        """
        return (
            self.mandate == choices.Mandate.CONTINGENCY
            and self.contingency_percentage > 0
        )

    @property
    def agreed(self) -> int:
        """Lo cerrado con el cliente. Una expectativa no esta cerrada."""
        if self.mandate == choices.Mandate.PAYMENT:
            return self.agreed_fee
        if self.mandate == choices.Mandate.CONTINGENCY:
            return 0 if self.is_contingency_expectation else self.contingency_value
        return 0

    @property
    def paid(self) -> int:
        """Lo que ya entro. Solo la modalidad de pago registra abonos."""
        return self.paid_amount if self.mandate == choices.Mandate.PAYMENT else 0

    @property
    def balance(self) -> int:
        """
        Lo que falta por cobrar. **No se guarda**: se calcula.

        Nunca es negativo: un abono mayor que lo pactado es un error de
        captura o un anticipo, y en ninguno de los dos casos el cliente pasa
        a tener saldo a favor en este panel.
        """
        return max(0, self.agreed - self.paid)

    @property
    def expectation(self) -> int:
        """Lo que se espera ganar si el pleito sale. No es deuda."""
        return self.contingency_value if self.is_contingency_expectation else 0

    @property
    def contingency_kind(self) -> str:
        """
        De que clase es la cuota litis: fija o por expectativa.

        Es la columna «Tipo cuota litis» del cuadro aprobado, y existe porque
        la misma modalidad significa dos cosas distintas segun el porcentaje.
        Quien lee el cuadro no tiene por que acordarse de esa regla; la
        columna se la dice.
        """
        if self.mandate != choices.Mandate.CONTINGENCY:
            return ''

        return (
            _('BY EXPECTATION') if self.is_contingency_expectation
            else _('FIXED')
        )

    @property
    def elapsed(self) -> str:
        """
        Cuanto lleva abierto el asunto, en anos y meses.

        En meses y no en dias: el campo de inicio es un mes --no se guarda el
        dia-- y decir «847 dias» sobre un dato que solo tiene precision de mes
        seria inventarse una exactitud que no hay.

        Se cuenta hasta hoy. Un inicio en el futuro --un error de captura-- da
        cero y no un negativo, que en la tabla se leeria como un asunto que
        empieza dentro de tres meses.
        """
        if not self.start_date:
            return '—'

        today = timezone.localdate()
        months = (
            (today.year - self.start_date.year) * 12
            + today.month - self.start_date.month
        )
        months = max(0, months)
        years, rest = divmod(months, 12)

        if years and rest:
            return _('%(years)s and %(months)s') % {
                'years': ngettext('%d year', '%d years', years) % years,
                'months': ngettext('%d month', '%d months', rest) % rest,
            }

        if years:
            return ngettext('%d year', '%d years', years) % years

        return ngettext('%d month', '%d months', months) % months

    def clean(self):
        """Que cada modalidad solo traiga las cifras que le corresponden."""
        from django.core.exceptions import ValidationError

        errors = {}

        if self.mandate in (choices.Mandate.PRO_BONO, choices.Mandate.GUARDIANSHIP):
            if self.agreed_fee or self.paid_amount or self.contingency_value:
                errors['mandate'] = _(
                    'This modality cannot carry any amount.'
                )

        if self.mandate == choices.Mandate.PAYMENT and self.contingency_value:
            errors['contingency_value'] = _(
                'A payment modality does not carry a contingency value.'
            )

        if self.mandate == choices.Mandate.CONTINGENCY and (
            self.agreed_fee or self.paid_amount
        ):
            errors['agreed_fee'] = _(
                'A contingency does not carry an agreed fee or payments.'
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f'{self.case} - {self.mandate}'

    class Meta:
        db_table = 'apps_project_case_manager_case_finance'
        verbose_name = _('Case finance')
        verbose_name_plural = _('Case finances')
        ordering = ['-updated']


class CaseNoteQuerySet(models.QuerySet):
    def for_client(self):
        """
        Las que el cliente puede ver en el portal, con las suyas primero.

        El filtro va en el queryset y no en la plantilla: una plantilla que no
        pinta algo lo ha recibido igualmente, y una nota interna puede decir
        cosas que no se le cuentan al cliente.

        El orden no es por fecha a secas: **las que le piden algo van
        arriba**, por recientes que sean las demas. Una peticion de documento
        por debajo de tres avisos informativos es una peticion que no se
        atiende, y ese es justo el caso en el que el asunto se queda parado
        esperando al cliente.
        """
        return self.filter(visible_to_client=True).annotate(
            pide_accion=models.Case(
                models.When(kind=choices.NoteKind.DOCUMENT, then=0),
                default=1,
                output_field=models.PositiveSmallIntegerField(),
            )
        ).order_by('pide_accion', '-created')


class CaseNoteModel(TimeStampedModel):
    """
    Una novedad del asunto, escrita para el cliente o para el despacho.

    Es lo que el portal no tenia y por eso el cliente llamaba: la pantalla
    ensenaba la etapa y nada mas, asi que un asunto parado tres meses porque
    un juzgado no responde y otro parado porque falta su cedula se veian
    exactamente igual.

    Dos campos deciden todo lo demas:

    - `visible_to_client` --- si sale en el portal. Hay notas que son para el
      expediente y no para el cliente.
    - `notified_at` --- cuando se le mando el correo, si se mando. Es una
      **fecha y no un booleano** porque interesa saber cuando se le dijo:
      «le avisamos» y «le avisamos el 3 de marzo» no valen lo mismo en una
      reclamacion.
    """

    id = models.UUIDField(
        'ID',
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        serialize=False,
        editable=False
    )

    case = models.ForeignKey(
        CaseModel,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name=_('case')
    )

    kind = models.CharField(
        _('kind'),
        max_length=20,
        choices=choices.NoteKind.choices,
        default=choices.NoteKind.INFO
    )

    title = models.CharField(
        _('title'),
        max_length=200
    )

    body = models.TextField(
        _('body'),
        help_text=_(
            'The client reads this as written. Keep it plain and say what, '
            'if anything, they have to do.'
        )
    )

    visible_to_client = models.BooleanField(
        _('visible to the client'),
        default=True,
        help_text=_('Uncheck for notes that belong to the file, not to them.')
    )

    notified_at = models.DateTimeField(
        _('notified at'),
        blank=True,
        null=True,
        editable=False,
        help_text=_('When the client was emailed about this note, if ever.')
    )

    created_by = models.ForeignKey(
        'users.UserModel',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='case_notes',
        verbose_name=_('written by'),
        editable=False
    )

    objects = CaseNoteQuerySet.as_manager()

    @property
    def style(self) -> dict:
        """El color y el icono con que se pinta, segun el tipo."""
        return choices.NOTE_STYLES.get(
            self.kind, choices.NOTE_STYLES[choices.NoteKind.INFO]
        )

    @property
    def needs_client_action(self) -> bool:
        """
        Si la nota le pide algo al cliente.

        Solo `DOCUMENT`. Sirve para que el portal la destaque por encima de
        las demas: una peticion perdida entre avisos es una peticion que no se
        atiende.
        """
        return self.kind == choices.NoteKind.DOCUMENT

    def __str__(self) -> str:
        return f'{self.get_kind_display()} - {self.title}'

    class Meta:
        db_table = 'apps_project_case_manager_case_note'
        verbose_name = _('Case note')
        verbose_name_plural = _('Case notes')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['case', '-created']),
        ]


auditlog.register(ClientModel, serialize_data=True)
auditlog.register(CaseModel, serialize_data=True)
auditlog.register(CaseFinanceModel, serialize_data=True)
auditlog.register(CaseNoteModel, serialize_data=True)

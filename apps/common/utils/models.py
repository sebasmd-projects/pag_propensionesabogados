import hashlib

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def hash_value(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class TimeStampedModel(models.Model):
    """Abstract model providing timestamp fields (created and updated) and additional metadata.

    Args:
        models.Model (class): Base Django model class.
    """

    history = AuditlogHistoryField()

    language_choices = [
        ('es', _('Spanish')),
        ('en', _('English')),
    ]

    language = models.CharField(
        _("language"),
        max_length=4,
        choices=language_choices,
        default='es',
        blank=True,
        null=True
    )

    created = models.DateTimeField(
        _('created'),
        default=timezone.now,
        editable=False
    )

    updated = models.DateTimeField(
        _('updated'),
        auto_now=True,
        editable=False
    )

    is_active = models.BooleanField(
        _("is active"),
        default=True
    )

    default_order = models.PositiveIntegerField(
        _('priority'),
        default=1,
        blank=True,
        null=True
    )

    class Meta:
        abstract = True
        ordering = ['default_order']


class IPBlockedModel(TimeStampedModel):
    """
    Una IP frenada, y lo que se sabe de ella.

    Los datos vivían **dentro** de ``session_info``, un JSON. Funcionaba para
    guardarlos y no servía para nada más: desde el admin no se podía ordenar
    por número de intentos, ni filtrar las que vienen de un proveedor cloud,
    ni ver de un vistazo cuándo empezó cada una. Para responder «¿esto es un
    escáner o alguien que se equivocó de URL?» había que abrir la fila y leer
    un JSON.

    Así que lo que se consulta está ahora en columnas y el JSON se queda como
    **el rastro crudo**: la lista de rutas, las cabeceras, los parámetros. Las
    columnas se derivan de él al anotar cada intento (``blocking.py``), no se
    escriben a mano por separado -- si se escribieran en dos sitios acabarían
    contando cosas distintas.
    """

    class ReasonsChoices(models.TextChoices):
        SERVER_HTTP_REQUEST = 'RA', _('Attempts to obtain forbidden urls')
        SECURITY_KEY_ATTEMPTS = 'SK', _(
            'Multiple failed security key entry attempts'
        )
        # Las dos de abajo son nuevas. La primera la levanta el detector de
        # ráfagas de 404 --enumerar sin acertar ningún término de la trampa--
        # y la segunda, una herramienta de escaneo que se identifica sola.
        PATH_ENUMERATION = 'PE', _('Enumerating paths that do not exist')
        SCANNER_SIGNATURE = 'SC', _('Known scanning tool')

        # Propio de pag: lo levanta el portal de consulta de procesos.
        CASE_QUERY_ATTEMPTS = 'CQ', _(
            'Multiple failed access key attempts on the case query portal'
        )

    is_active = models.BooleanField(_("is blocked"), default=True)
    current_ip = models.CharField(_('current user IP'), max_length=150)
    reason = models.CharField(
        _("reason"), max_length=4, choices=ReasonsChoices.choices, default=ReasonsChoices.SERVER_HTTP_REQUEST)
    blocked_until = models.DateTimeField(
        _("blocked until"), null=True, blank=True)
    session_info = models.JSONField(
        _("session information"), default=dict, blank=True)

    # --- Lo que antes había que leer del JSON --------------------------
    attempt_count = models.PositiveIntegerField(
        _('attempts'), default=0, db_index=True)

    unique_paths = models.PositiveIntegerField(
        _('unique paths'),
        default=0,
        help_text=_(
            'Distinct paths tried. Many attempts on one path is someone '
            'retrying; a few attempts on many paths is a scan.'
        ),
    )

    #: `created` es cuándo se abrió la fila y `updated` cambia con cualquier
    #: guardado, incluido uno hecho a mano desde el admin. Estas dos son de la
    #: actividad de la IP y sólo las mueve un intento suyo.
    first_seen = models.DateTimeField(
        _('first detection'), null=True, blank=True, db_index=True)
    last_seen = models.DateTimeField(
        _('last detection'), null=True, blank=True, db_index=True)

    user_agent = models.CharField(
        _('user agent'), max_length=500, blank=True, default='')

    matched_pattern = models.CharField(
        _('pattern'),
        max_length=150,
        blank=True,
        default='',
        help_text=_('What tripped the block: the trap term, or the signature.'),
    )

    # --- De qué red viene (ver netintel.py) ----------------------------
    country = models.CharField(
        _('country'), max_length=2, blank=True, default='', db_index=True)

    network_owner = models.CharField(
        _('network / ASN'), max_length=100, blank=True, default='')

    is_datacenter = models.BooleanField(
        _('datacenter or cloud'),
        default=False,
        db_index=True,
        help_text=_(
            'The IP belongs to a hosting provider range. A person browses '
            'from a home or office address; a server does not browse.'
        ),
    )

    # ------------------------------------------------------------------
    @property
    def is_currently_blocked(self) -> bool:
        """
        Si el bloqueo está en pie **ahora**, que no es lo mismo que ``is_active``.

        ``is_active`` es el interruptor: dice si alguien lo desactivó a mano.
        Que el bloqueo siga vigente depende además del reloj, y eso no lo puede
        guardar una columna sin que algo la vaya actualizando -- un cron o un
        guardado en cada petición, las dos cosas peores que la pregunta.

        Se calcula al leerla, así que el admin enseña siempre el estado real
        sin que nadie tenga que refrescar nada. Es también la condición exacta
        que aplica el middleware, escrita una sola vez.
        """
        if not self.is_active or not self.blocked_until:
            return False

        return self.blocked_until > timezone.now()

    @property
    def time_remaining(self):
        """Cuánto queda de bloqueo, o ``None`` si ya no hay."""
        if not self.is_currently_blocked:
            return None

        return self.blocked_until - timezone.now()

    def save(self, *args, **kwargs):
        """
        Rellena el origen de la IP la primera vez, venga la fila de donde venga.

        Va en ``save()`` y no sólo en el camino del bloqueo porque las filas se
        crean por cuatro sitios --la trampa, el detector de ráfagas, la firma
        de escáner y a mano desde el admin-- y una fila sin origen es
        justamente la que no se puede leer. Se calcula una sola vez: la tabla
        de prefijos es un recorrido en memoria, pero no cambia entre intentos.

        Respeta ``update_fields``: si quien guarda no pidió estos campos, no se
        escriben. Es lo que evita pisar un cambio hecho a mano desde el admin
        mientras una petición estaba en curso.
        """
        fields = kwargs.get('update_fields')

        if self.current_ip and not self.network_owner and not self.country:
            from apps.common.utils import netintel

            intel = netintel.describe(self.current_ip)

            self.network_owner = (intel['network_owner'] or '')[:100]
            self.is_datacenter = intel['is_datacenter']
            self.country = (intel['country'] or '')[:2]

            if fields is not None:
                kwargs['update_fields'] = set(fields) | {
                    'network_owner', 'is_datacenter', 'country'}

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.current_ip} - Blocked until {self.blocked_until}"

    class Meta:
        db_table = 'apps_common_utils_ipblocked'
        verbose_name = 'Blocked IP'
        verbose_name_plural = 'Blocked IPs'
        # Por fecha de alta y, a igualdad, por la última vez que se tocó la
        # fila. `TimeStampedModel` ordena por `default_order`, que aquí no
        # significa nada: todas las filas lo tienen a 1, así que el orden
        # acababa siendo el que quisiera la base de datos.
        #
        # Las demás columnas del listado son ordenables desde el admin, así
        # que ver «lo último que se movió» es un clic en `last detection`.
        ordering = ['-created', '-updated']
        indexes = [
            # La consulta del middleware, que corre en **cada** petición que no
            # sea de un estático. Sin índice es un recorrido de la tabla entera
            # por petición, y esta tabla sólo crece.
            models.Index(
                fields=['current_ip', 'is_active', 'blocked_until'],
                name='ipblocked_lookup_idx',
            ),
        ]


class WhiteListedIPModel(TimeStampedModel):
    current_ip = models.CharField(
        _('current user IP'),
        max_length=150
    )

    reason = models.CharField(
        _("reason"),
        max_length=150,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.current_ip}"

    class Meta:
        db_table = 'apps_utils_whitelistedip'
        verbose_name = 'WhiteListed IP'
        verbose_name_plural = 'WhiteListed IPs'


auditlog.register(
    IPBlockedModel,
    serialize_data=True
)

auditlog.register(
    WhiteListedIPModel,
    serialize_data=True
)

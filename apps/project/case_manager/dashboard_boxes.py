"""
Los cuadros del panel: uno por categoria de asunto.

Por que existe
--------------
Hasta ahora el panel ensenaba dos tablas --quien debe y quien esta en
expectativa-- y un asunto que no fuera ninguna de las dos no salia en
ninguna parte: los pagados, el ad honorem, la curaduria, los inactivos, los
que se marcaron «No incluir en panel»... Estaban en la base y no en la
pantalla, y nada decia que faltaban.

Los dos primeros cuadros del panel --deudores y expectativas-- siguen
armandose en la vista, con sus consultas de siempre; aqui estan **las demas**
categorias. Cada cuadro sale de una consulta de `CaseFinanceQuerySet` (o de
`CaseModel` cuando el asunto ni siquiera tiene bloque economico), y el
conjunto **cubre todos los asuntos**: `unclassified()` recoge los que tienen
la modalidad puesta pero las cifras sin rellenar, y `no_finance` los que no
tienen bloque. `tests/test_dashboard_boxes.py` lo comprueba con los datos de
prueba.

Que un asunto salga en dos cuadros solo pasa donde el cuadro lo justifica:
la cuota litis al 0 % ya cobrada sale en «Pagados» (estado de cobro) y en
«Cuota litis al 0 %» (la modalidad, con su valor fijo).

Las filas se arman aqui, como celdas, y no en la plantilla, para que todas
las tablas compartan una sola plantilla (`partials/category_box.html`) y para
que el test pueda mirar el contenido sin renderizar.

Rendimiento
-----------
Todo sale con `select_related`: `case` y `case__client` desde el bloque
economico, `client` y `finance` desde el asunto. Las celdas solo leen
atributos ya cargados, asi que el numero de consultas no crece con las filas.
"""

from dataclasses import dataclass, field

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from . import choices
from .models import CaseFinanceModel, CaseModel


@dataclass
class Box:
    """Un cuadro del panel: titulo, columnas y filas ya armadas."""

    key: str
    title: str
    icon: str
    tone: str
    empty: str
    hint: str
    columns: list
    rows: list = field(default_factory=list)
    order: str = '0 asc'

    def __post_init__(self):
        # Una columna es un rotulo o un par (rotulo, alineacion).
        self.columns = [
            {'label': col[0], 'align': col[1]} if isinstance(col, tuple)
            else {'label': col, 'align': 'start'}
            for col in self.columns
        ]

    @property
    def table_id(self) -> str:
        return f'tabla-{self.key.replace("_", "-")}'

    @property
    def case_ids(self) -> set:
        return {row['case_id'] for row in self.rows}


def _client_cell(case, sub=None):
    return {
        'text': case.client.full_name,
        'url': reverse('case_manager:gestor_case_update', args=[case.pk]),
        'sub': case.service_display if sub is None else sub,
    }


def _money(value):
    return {'money': True, 'text': value, 'order': value, 'align': 'end'}


def _text(value, order=None, align='start', badge=''):
    return {'text': value, 'order': order, 'align': align, 'badge': badge}


def _row(case, *cells, sub=None):
    return {
        'case_id': case.pk,
        'cells': [_client_cell(case, sub), *cells],
    }


def _authorized(case):
    if case.paz_y_salvo_authorized:
        return _text(_('Authorized'), 1, badge='success')
    return _text(_('Not authorized'), 0, badge='secondary')


def _stage(case):
    return _text(case.get_stage_display(), case.stage)


def _fee_arrangement(finance):
    if finance is None or not finance.mandate:
        return _text('—')
    label = finance.get_mandate_display()
    if finance.mandate == choices.Mandate.CONTINGENCY:
        label = f'{label} ({finance.contingency_percentage} %)'
    return _text(label)


def _date(value):
    return _text(value.strftime('%d/%m/%Y'), value.strftime('%Y%m%d'))


def _finances(queryset):
    return queryset.select_related('case', 'case__client').order_by(
        'case__client__full_name', 'case_id'
    )


def build_boxes() -> list[Box]:
    """Los cuadros de las demas categorias, en el orden en que se pintan."""
    finances = CaseFinanceModel.objects
    boxes = []

    paid = Box(
        'paid_in_full', _('Paid in full'), 'check-circle', 'success',
        _('No cases paid in full.'),
        _('Nothing left to collect, with the settlement letter status '
          '(it is authorized from the case list).'),
        [_('Client'), (_('Agreed'), 'end'), (_('Paid'), 'end'),
         _('Settlement letter')],
        order='2 desc',
    )
    for row in _finances(finances.paid_in_full()):
        paid.rows.append(_row(
            row.case, _money(row.agreed), _money(row.paid),
            _authorized(row.case),
        ))
    boxes.append(paid)

    for key, title, icon, method, empty in (
        ('pro_bono', _('Ad honorem'), 'heart', 'pro_bono',
         _('No ad honorem cases.')),
        ('guardianship', _('Curaduría'), 'shield-check', 'guardianship',
         _('No curaduría cases.')),
    ):
        box = Box(
            key, title, icon, 'secondary', empty,
            _('No money involved: listed so that they are not lost.'),
            [_('Client'), _('Stage'), _('Elapsed')],
        )
        for row in _finances(getattr(finances, method)()):
            box.rows.append(_row(
                row.case, _stage(row.case), _text(row.elapsed),
            ))
        boxes.append(box)

    fixed = Box(
        'fixed_contingency', _('Contingency at 0 % (fixed value)'),
        'lock', 'primary',
        _('No fixed-value contingency cases without a balance.'),
        _('Fixed value with nothing owed: already covered, or without a '
          'value yet. Those that still owe are in the balance table.'),
        [_('Client'), (_('Fixed value'), 'end'), (_('Paid'), 'end'),
         _('Status')],
        order='1 desc',
    )
    for row in _finances(finances.fixed_contingency()):
        covered = row.contingency_value > 0
        fixed.rows.append(_row(
            row.case, _money(row.contingency_value),
            _money(row.paid_amount),
            _text(_('Covered') if covered else _('No value set'),
                  1 if covered else 0,
                  badge='success' if covered else 'warning'),
        ))
    boxes.append(fixed)

    unclassified = Box(
        'unclassified', _('Amounts not filled in'), 'question-circle',
        'warning', _('Every case in the dashboard has its amounts filled in.'),
        _('The fee arrangement is set but no amount is: fill them in or '
          'they will not add up anywhere.'),
        [_('Client'), _('Fee arrangement'), _('Stage')],
    )
    for row in _finances(finances.unclassified()):
        unclassified.rows.append(_row(
            row.case, _fee_arrangement(row), _stage(row.case),
        ))
    boxes.append(unclassified)

    hidden = Box(
        'hidden', _('Not included in the financial dashboard'),
        'eye-slash', 'secondary',
        _('No cases are excluded from the financial dashboard.'),
        _('Marked «Do not include in the financial dashboard»: their '
          'amounts are not in the totals above.'),
        [_('Client'), _('Fee arrangement'),
         (_('Agreed / expectation'), 'end'), (_('Paid'), 'end')],
    )
    for row in _finances(finances.hidden_from_dashboard()):
        hidden.rows.append(_row(
            row.case, _fee_arrangement(row),
            _money(row.agreed or row.expectation), _money(row.paid),
        ))
    boxes.append(hidden)

    inactive = Box(
        'inactive', _('Inactive or closed cases'), 'archive', 'secondary',
        _('No inactive cases.'),
        _('Cases no longer in force. They are out of the totals whatever '
          'their fee arrangement.'),
        [_('Client'), _('Stage'), _('Fee arrangement'), _('Last update')],
        order='3 desc',
    )
    for case in CaseModel.objects.filter(is_active=False).select_related(
            'client', 'finance').order_by('client__full_name', 'pk'):
        inactive.rows.append(_row(
            case, _stage(case),
            _fee_arrangement(getattr(case, 'finance', None)),
            _date(case.updated),
        ))
    boxes.append(inactive)

    no_finance = Box(
        'no_finance', _('Cases without financial block'),
        'question-diamond', 'warning',
        _('Every case has its financial block.'),
        _('The fee arrangement has not been filled in yet, so they add up '
          'nowhere.'),
        [_('Client'), _('Stage'), _('Created')],
    )
    for case in CaseModel.objects.filter(
            is_active=True, finance__isnull=True).select_related(
            'client').order_by('client__full_name', 'pk'):
        no_finance.rows.append(_row(
            case, _stage(case), _date(case.created),
        ))
    boxes.append(no_finance)

    return boxes

"""Serie temporal del comparativo financiero del gestor."""

from __future__ import annotations

import calendar
import math
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.utils import timezone

from .choices import Mandate


SERIES = (
    ('agreed', 'Pactado', 'secondary'),
    ('paid', 'Pagado', 'success'),
    ('balance', 'Por cobrar', 'warning'),
    ('expectation', 'Expectativa', 'info'),
    ('upcoming', 'Próximo a pago', 'primary'),
)


def _as_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _created_date(finance):
    created = finance.created
    if isinstance(created, datetime) and timezone.is_aware(created):
        created = timezone.localtime(created)
    return created.date() if isinstance(created, datetime) else created


def _events(finances, today):
    """Convierte contratos e historial de pagos en movimientos fechados."""
    events = []
    for finance in finances:
        baseline = finance.start_date or _created_date(finance) or today
        if finance.mandate == Mandate.PAYMENT:
            agreed = finance.agreed_fee
            expectation = 0
        elif finance.mandate == Mandate.CONTINGENCY:
            agreed = finance.contingency_value if finance.contingency_percentage == 0 else 0
            expectation = finance.contingency_value if finance.contingency_percentage > 0 else 0
        else:
            agreed = expectation = 0

        if agreed:
            events.extend((
                (baseline, 'agreed', agreed),
                (baseline, 'balance', max(0, agreed - finance.paid_amount)),
            ))
        if expectation:
            events.append((baseline, 'expectation', expectation))

        history_paid = 0
        for row in finance.payment_history or []:
            if not isinstance(row, dict):
                continue
            amount = row.get('amount', 0)
            if type(amount) is not int or amount <= 0:
                continue
            kind = row.get('kind')
            if kind in ('payment', 'administrative'):
                events.append((_as_date(row.get('date')) or baseline, 'paid', amount))
                history_paid += amount
            elif kind == 'expected':
                events.append((_as_date(row.get('date')) or today, 'upcoming', amount))

        # Importes antiguos pueden existir sin historial detallado.
        legacy_paid = max(0, finance.paid_amount - history_paid)
        if legacy_paid:
            events.append((baseline, 'paid', legacy_paid))
    return events


def _month_end(value):
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def _range(request, events, today):
    default_start = today.replace(day=1)
    default_end = _month_end(today)
    if request.GET.get('range') == 'all':
        dated = [event_date for event_date, _, _ in events]
        return (
            min(dated, default=today),
            max([today, *dated]),
            True,
        )

    start = _as_date(request.GET.get('start')) or default_start
    end = _as_date(request.GET.get('end')) or default_end
    if start > end:
        return default_start, default_end, False
    return start, end, False


def _granularity(start, end, is_all=False):
    """Unidad de agrupación según la duración del rango.

    Hasta 7 días: días. Hasta 31: semanas de lunes a domingo. Hasta 366:
    meses. Más (o "Completo"): años.
    """
    days = (end - start).days + 1
    if is_all or days > 366:
        return 'year', 'Años'
    if days <= 7:
        return 'day', 'Días'
    if days <= 31:
        return 'week', 'Semanas'
    return 'month', 'Meses'


MONTHS = ('ene', 'feb', 'mar', 'abr', 'may', 'jun',
          'jul', 'ago', 'sep', 'oct', 'nov', 'dic')
WEEKDAYS = ('lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom')


def _bucket_start(value, granularity):
    if granularity == 'week':
        return value - timedelta(days=value.weekday())
    if granularity == 'month':
        return value.replace(day=1)
    if granularity == 'year':
        return value.replace(month=1, day=1)
    return value


def _next_bucket(value, granularity):
    if granularity == 'day':
        return value + timedelta(days=1)
    if granularity == 'week':
        return value + timedelta(days=7)
    if granularity == 'month':
        return (value.replace(day=28) + timedelta(days=4)).replace(day=1)
    return value.replace(year=value.year + 1)


def _span(first, last, with_year=False):
    """'01–07 sep', '28 sep–04 oct' o '30 sep' (con año si se pide)."""
    year = f' {last.year}' if with_year else ''
    if first == last:
        return f'{first.day:02d} {MONTHS[first.month - 1]}{year}'
    if (first.year, first.month) == (last.year, last.month):
        return f'{first.day:02d}–{last.day:02d} {MONTHS[last.month - 1]}{year}'
    first_year = f' {first.year}' if with_year and first.year != last.year else ''
    return (f'{first.day:02d} {MONTHS[first.month - 1]}{first_year}–'
            f'{last.day:02d} {MONTHS[last.month - 1]}{year}')


def _labels(first, last, granularity):
    """Etiqueta corta del eje y título completo del tooltip."""
    if granularity == 'day':
        return (first.strftime('%d/%m'),
                f'{WEEKDAYS[first.weekday()]} {first:%d/%m/%Y}')
    if granularity == 'week':
        return _span(first, last), _span(first, last, with_year=True)
    if granularity == 'month':
        return (f'{MONTHS[first.month - 1]} {first.year}',
                f'{MONTHS[first.month - 1]} {first.year}')
    return str(first.year), str(first.year)


def _nice_step(raw):
    """Paso 1, 2, 2.5, 5 o 10 por potencia de diez, sin quedarse corto."""
    magnitude = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 2.5, 5, 10):
        if raw <= factor * magnitude:
            return factor * magnitude
    return 10 * magnitude


def axis_ticks(maximum):
    """Marcas del eje Y (0 hasta un máximo redondo) con su etiqueta.

    Misma lógica que `niceScale` en scripts/financial_chart.js, que la
    recalcula al filtrar series.
    """
    maximum = maximum or 4_000_000  # sin datos: escala de ejemplo
    step = _nice_step(maximum / 4)
    count = max(1, math.ceil(maximum / step))
    top = step * count
    top = int(top) if top == int(top) else top
    if top >= 1_000_000:
        divisor, suffix = 1_000_000, ' M'
    elif top >= 10_000:
        divisor, suffix = 1_000, ' K'
    else:
        divisor, suffix = 1, ''
    ticks = []
    for index in range(count + 1):
        value = step * index
        value = int(value) if value == int(value) else value
        scaled = round(value / divisor, 1)
        text = (str(int(scaled)) if scaled == int(scaled)
                else str(scaled).replace('.', ','))
        ticks.append({
            'value': value,
            'label': f'${text}{suffix}',
            'position': round(index * 100 / count, 4),
        })
    return top, ticks


def quick_periods(today, start, end, is_all):
    """Botones de periodo rápido (enlaces GET) y cuál está activo."""
    week_start = today - timedelta(days=today.weekday())
    definitions = (
        ('day', 'Día', today, today),
        ('week', 'Semana', week_start, week_start + timedelta(days=6)),
        ('month', 'Mes', today.replace(day=1), _month_end(today)),
        ('year', 'Año', today.replace(month=1, day=1),
         today.replace(month=12, day=31)),
    )
    periods = [
        {
            'key': key,
            'label': label,
            'url': f'?start={first.isoformat()}&end={last.isoformat()}',
            'active': not is_all and (first, last) == (start, end),
        }
        for key, label, first, last in definitions
    ]
    periods.append({'key': 'all', 'label': 'Completo', 'url': '?range=all',
                    'active': is_all})
    return periods


def build_financial_chart(request, finances, today=None):
    """Datos listos para la gráfica, con rango y agrupación automáticos."""
    today = today or timezone.localdate()
    events = _events(finances, today)
    start, end, is_all = _range(request, events, today)
    granularity, granularity_label = _granularity(start, end, is_all)

    cursor = _bucket_start(start, granularity)
    last_bucket = _bucket_start(end, granularity)
    keys = []
    while cursor <= last_bucket:
        keys.append(cursor)
        cursor = _next_bucket(cursor, granularity)

    values = {key: defaultdict(int) for key in keys}
    for event_date, series, amount in events:
        if start <= event_date <= end:
            values[_bucket_start(event_date, granularity)][series] += amount

    maximum = max(
        (amount for bucket in values.values() for amount in bucket.values()),
        default=0,
    )
    top, ticks = axis_ticks(maximum)
    buckets = []
    for key in keys:
        # Los grupos parciales (semanas, meses) se recortan al rango pedido.
        first = max(key, start)
        last = min(_next_bucket(key, granularity) - timedelta(days=1), end)
        label, title = _labels(first, last, granularity)
        bucket_values = []
        for series, series_label, tone in SERIES:
            amount = values[key][series]
            bucket_values.append({
                'key': series,
                'label': series_label,
                'tone': tone,
                'value': amount,
                'height': round(amount * 100 / top, 2) if amount else 0,
            })
        buckets.append({
            'label': label,
            'title': title,
            'start': first.isoformat(),
            'end': last.isoformat(),
            'values': bucket_values,
        })

    totals = [
        {
            'key': series,
            'label': label,
            'tone': tone,
            'value': sum(values[key][series] for key in keys),
        }
        for series, label, tone in SERIES
    ]

    return {
        'start': start.isoformat(),
        'end': end.isoformat(),
        'is_all': is_all,
        'granularity': granularity,
        'granularity_label': granularity_label,
        'buckets': buckets,
        'axis': ticks,
        'totals': totals,
        'periods': quick_periods(today, start, end, is_all),
        'legend': [
            {'key': key, 'label': label, 'tone': tone}
            for key, label, tone in SERIES
        ],
    }

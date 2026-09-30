"""Serie temporal del comparativo financiero del gestor."""

from __future__ import annotations

import calendar
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


def _granularity(start, end):
    days = (end - start).days + 1
    if days <= 31:
        return 'day', 'Días'
    if days <= 120:
        return 'week', 'Semanas'
    if days <= 730:
        return 'month', 'Meses'
    return 'year', 'Años'


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


def _label(value, granularity):
    if granularity == 'day':
        return value.strftime('%d/%m')
    if granularity == 'week':
        end = value + timedelta(days=6)
        return f'{value:%d/%m}–{end:%d/%m}'
    if granularity == 'month':
        return value.strftime('%m/%Y')
    return str(value.year)


def build_financial_chart(request, finances, today=None):
    """Datos listos para la gráfica, con rango y agrupación automáticos."""
    today = today or timezone.localdate()
    events = _events(finances, today)
    start, end, is_all = _range(request, events, today)
    granularity, granularity_label = _granularity(start, end)

    first_bucket = _bucket_start(start, granularity)
    last_bucket = _bucket_start(end, granularity)
    keys = []
    cursor = first_bucket
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
    ) or 1
    buckets = []
    for key in keys:
        bucket_values = []
        for series, label, tone in SERIES:
            amount = values[key][series]
            bucket_values.append({
                'key': series,
                'label': label,
                'tone': tone,
                'value': amount,
                'height': round(amount * 100 / maximum) if amount else 0,
            })
        buckets.append({'label': _label(key, granularity), 'values': bucket_values})

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
        'totals': totals,
        'legend': [
            {'key': key, 'label': label, 'tone': tone}
            for key, label, tone in SERIES
        ],
    }

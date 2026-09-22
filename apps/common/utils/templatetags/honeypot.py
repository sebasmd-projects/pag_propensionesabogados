"""
La etiqueta que pinta el campo trampa.

Se llama `honeypot` para que `{% load honeypot %}` siga funcionando igual que
cuando lo daba el paquete: las plantillas que ya la usaban no cambian. El
porque de haberlo traido adentro esta en `apps/common/utils/honeypot.py`.
"""

from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag('honeypot/honeypot_field.html')
def render_honeypot_field(field_name=None):
    """Pinta el campo trampa, con `HONEYPOT_FIELD_NAME` si no se da nombre."""
    value = getattr(settings, 'HONEYPOT_VALUE', '')
    if callable(value):
        value = value()
    return {
        'fieldname': field_name or settings.HONEYPOT_FIELD_NAME,
        'value': value,
    }

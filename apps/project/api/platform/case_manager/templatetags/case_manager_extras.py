"""
Filtros del gestor.

Solo formato de presentacion. Ninguna decision, ninguna consulta: lo que se
pinta ya viene decidido de la vista.
"""

from django import template

register = template.Library()


@register.filter
def grouped_identification(value) -> str:
    """
    La cedula con puntos de millar: `16484186` -> `16.484.186`.

    Es `formatoCedulaPS()` del JavaScript. Se guarda sin puntos --porque asi
    se busca-- y se ensena con ellos, que es como esta impresa en el
    documento.
    """
    digits = ''.join(character for character in str(value or '') if character.isdigit())
    if not digits:
        return ''

    groups = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)
    return '.'.join(groups)


@register.filter
def client_identification(client) -> str:
    """
    El documento de un cliente con su tipo: `CC 1.152.225.004`,
    `NIT 900.123.456-7`, `CE 1.234.567`, `PA AB123456`.
    """
    return getattr(client, 'display_identification', '') or ''


@register.filter
def client_identification_search(client) -> str:
    """
    Texto para la busqueda de DataTables (`data-search`): el numero sin
    puntos, el numero con ellos y el tipo, para que `1152225004` y
    `1.152.225` encuentren al mismo cliente.
    """
    if client is None:
        return ''
    number = getattr(client, 'identification', '') or ''
    return f'{number} {client.display_identification}'.strip()


@register.filter
def client_number(client) -> str:
    """El documento sin el tipo, con puntos y DV: `900.123.456-7`."""
    if client is None:
        return ''
    from ..identification import format_identification
    return format_identification(
        client.identification_type, client.identification,
        client.verification_digit, with_type=False,
    )

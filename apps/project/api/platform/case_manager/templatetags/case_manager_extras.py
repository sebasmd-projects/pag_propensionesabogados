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

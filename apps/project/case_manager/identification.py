"""
Documentos de identidad: normalizar, calcular el digito de verificacion y dar
formato.

Es codigo puro (sin base de datos ni plantillas) para que lo compartan el
modelo, los formularios, el portal, los informes y los filtros sin importarse
entre si.

El NIT lleva un digito de verificacion (DV) que **no** forma parte del numero:
`identification` guarda solo el numero (`900123456`) y el DV vive aparte
(`verification_digit`). Se calcula con el modulo 11 de la DIAN.
"""

import re

#: Pesos de la DIAN, aplicados de derecha a izquierda sobre el NIT.
NIT_WEIGHTS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)

#: Como mucho 15 digitos: es lo que cubren los pesos.
NIT_MAX_DIGITS = len(NIT_WEIGHTS)

CC, NIT, CE, PA = 'CC', 'NIT', 'CE', 'PA'

_NIT_WITH_DV = re.compile(r'^(\d+)-(\d)$')


def only_digits(value) -> str:
    return ''.join(c for c in str(value or '') if c.isdigit())


def nit_check_digit(number) -> str:
    """El DV del NIT segun el modulo 11 de la DIAN, o '' si no se puede."""
    digits = only_digits(number)
    if not digits or len(digits) > NIT_MAX_DIGITS:
        return ''
    total = sum(
        int(d) * w for d, w in zip(reversed(digits), NIT_WEIGHTS)
    )
    remainder = total % 11
    return str(remainder if remainder < 2 else 11 - remainder)


def normalize_number(raw, id_type: str = CC) -> str:
    """
    El numero tal y como se guarda: sin puntos, espacios ni guiones.

    Solo se quitan separadores (puntos, espacios, guiones) y se pasa a
    mayusculas; **no** se tiran las letras de un CC/NIT/CE, para que el
    modelo pueda rechazarlas en vez de guardar un numero distinto del escrito.
    El pasaporte, ademas, descarta todo lo que no sea letra o digito.
    """
    text = str(raw or '')
    if id_type == PA:
        return ''.join(c for c in text if c.isalnum()).upper()
    return re.sub(r'[\s.\-]', '', text).upper()


def split_lookup(raw) -> tuple[str, str]:
    """
    Lo que escribe quien consulta el portal -> (numero, dv).

    Acepta `900123456`, `900.123.456-7`, `900 123 456 - 7`, `1.152.225.004` o
    un pasaporte `ab-123456`. Solo se separa un DV cuando lo escrito son
    digitos, un guion y **un** digito final; en cualquier otro caso el guion
    es ruido y se descarta.
    """
    text = re.sub(r'[\s.]', '', str(raw or '')).upper()
    match = _NIT_WITH_DV.match(text)
    if match:
        return match.group(1), match.group(2)
    return ''.join(c for c in text if c.isalnum()), ''


def _group_thousands(digits: str) -> str:
    groups = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)
    return '.'.join(groups)


def format_identification(id_type, number, verification_digit='',
                          with_type=True) -> str:
    """
    `CC 1.152.225.004`, `NIT 900.123.456-7`, `CE 1.234.567`, `PA AB123456`.
    """
    number = str(number or '')
    if not number:
        return ''
    id_type = id_type or CC
    if id_type == PA:
        body = number.upper()
    else:
        digits = only_digits(number)
        body = _group_thousands(digits) if digits else number
    if id_type == NIT and verification_digit:
        body = f'{body}-{verification_digit}'
    return f'{id_type} {body}' if with_type else body

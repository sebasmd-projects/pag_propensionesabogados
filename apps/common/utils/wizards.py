"""
Lo que hay que decirle a `formtools` cuando los pasos cambian a mitad de vuelo.

Desde **django-formtools 2.6**, `WizardView.get_form_list()` resuelve las
condiciones una vez por peticion y guarda el resultado en
`_resolved_form_list`. La firma de esa cache es::

    (id(self.condition_dict), tuple(sorted(self.condition_dict.items())))

O sea: la **identidad** del diccionario de condiciones y de sus valores. No lo
que esas condiciones devuelven. Una condicion que es un invocable y decide
mirando la sesion puede cambiar de respuesta sin que la firma se mueva, y la
cache seguira sirviendo la lista vieja.

El asistente de acceso hace exactamente eso: entra y sale del modo «codigo al
correo» dentro de la misma peticion, y ese modo decide si el paso `otp`
existe. Con la cache puesta y sin invalidar, el asistente pone como paso
actual uno que su propia lista dice que no existe, y sale un
`KeyError: 'otp'`.

No es un fallo de la biblioteca: es que una condicion que cambia dentro de la
peticion rompe cualquier cache que no lo sepa. La respuesta es avisarla, que
es lo que `formtools` hace en su propio `post()` tras guardar un paso.
"""

#: Donde `formtools` guarda la lista resuelta y su firma. Son privados; la
#: alternativa --recalcular la lista a mano-- seria mas fragil, porque habria
#: que reproducir su logica en vez de pedirle que la repita.
CACHE_ATTRIBUTES = ('_resolved_form_list', '_condition_dict_signature')


def forget_resolved_steps(wizard) -> None:
    """
    Olvida los pasos que el asistente tenga cacheados.

    Llamalo **justo despues** de cambiar algo que afecte a que pasos hay, y
    antes de volver a pedir un formulario. Es seguro llamarlo de mas: si no
    hay nada cacheado, no hace nada.
    """
    for attribute in CACHE_ATTRIBUTES:
        if hasattr(wizard, attribute):
            delattr(wizard, attribute)

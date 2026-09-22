"""
El formulario del portal publico de consulta.

Lo que aqui se valida lo validaba antes el navegador, con el expediente de
**todos** los clientes ya descargado::

    let D = JSON.parse(localStorage.getItem("propDemo") || '...');
    ...
    const esperada = inicial + c.slice(-4);
    if (clave !== esperada) { alert("Clave de acceso incorrecta."); return; }

O sea: el dato viajaba primero y se decidia despues, en la maquina de quien
preguntaba. Ahora viaja despues de decidir, y decide el servidor.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ClientModel

#: Una sola respuesta para los tres noes: no existe esa identificacion, la
#: clave no es, o el servicio no esta vigente.
#:
#: La pantalla anterior daba tres mensajes distintos, y eso convierte el
#: formulario en un buscador de personas: probando identificaciones, "clave
#: incorrecta" confirma que esa cedula es cliente del despacho. Quien tenga su
#: clave entra igual; quien no la tenga, ya no averigua nada probando.
INVALID_CREDENTIALS = _(
    'We could not find a service with that identification and access key.'
)


class PublicCaseQueryForm(forms.Form):
    """Identificacion y clave. Nada mas sale de aqui hacia la base."""

    identification = forms.CharField(
        label=_('identification number'),
        max_length=20,
    )

    access_key = forms.CharField(
        label=_('access key'),
        max_length=40,
        widget=forms.PasswordInput(render_value=False),
    )

    def clean_identification(self) -> str:
        """
        Se queda solo con los digitos.

        Quien escribe su cedula con puntos esta escribiendo la misma cedula, y
        el campo de la base esta normalizado.
        """
        raw = self.cleaned_data['identification']
        digits = ''.join(character for character in raw if character.isdigit())
        if not digits:
            raise forms.ValidationError(INVALID_CREDENTIALS)
        return digits

    def get_client(self) -> ClientModel | None:
        """
        El cliente al que corresponden estas credenciales, o `None`.

        Devuelve `None` en los tres casos --no existe, clave equivocada, sin
        vigencia-- y a proposito no dice cual: quien llama no tiene que poder
        distinguirlos ni aunque quiera.

        Cuando la identificacion no existe se comprueba igualmente una clave
        contra una cadena fija. Sin eso, un "no existe" responde antes que un
        "clave incorrecta", y el reloj cuenta lo mismo que contaria el
        mensaje.
        """
        from django.utils.crypto import constant_time_compare

        identification = self.cleaned_data['identification']
        access_key = self.cleaned_data['access_key']

        client = ClientModel.objects.filter(
            identification=identification
        ).first()

        if client is None:
            constant_time_compare(access_key, 'no-such-client')
            return None

        if not client.check_access_key(access_key):
            return None

        if not client.is_active:
            return None

        return client

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
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from .models import CaseFinanceModel, CaseModel, ClientModel

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


# ---------------------------------------------------------------------------
# El gestor interno
#
# Los de abajo son los formularios del despacho, no los del portal. Van en el
# mismo fichero porque son formularios, pero no comparten nada con el de
# arriba: aquel recibe dos campos de un visitante sin sesion, y estos editan
# el expediente entero de alguien que ya entro.
# ---------------------------------------------------------------------------


class BootstrapFormMixin:
    """
    Pone las clases de Bootstrap en los campos, una sola vez.

    Django pinta `<input>` pelado, y Bootstrap necesita `form-control` en las
    cajas de texto, `form-select` en los desplegables y `form-check-input` en
    las casillas. Escribirlo campo a campo en cada formulario son treinta
    lineas que se olvidan a la primera que alguien anada un campo nuevo; aqui
    se deduce del widget.

    Tambien marca en rojo lo que no valido (`is-invalid`), que es lo que hace
    que el mensaje de error de Bootstrap se vea.
    """

    #: Widgets que no llevan `form-control`, con la clase que si les toca.
    CLASES_POR_WIDGET = {
        'Select': 'form-select',
        'SelectMultiple': 'form-select',
        'NullBooleanSelect': 'form-select',
        'CheckboxInput': 'form-check-input',
        'RadioSelect': 'form-check-input',
        'FileInput': 'form-control',
        'ClearableFileInput': 'form-control',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for nombre, campo in self.fields.items():
            widget = campo.widget
            clase = self.CLASES_POR_WIDGET.get(
                type(widget).__name__, 'form-control'
            )
            existentes = widget.attrs.get('class', '')
            clases = f'{existentes} {clase}'.strip()

            if self.is_bound and nombre in self.errors:
                clases += ' is-invalid'

            widget.attrs['class'] = clases


class ClientForm(BootstrapFormMixin, forms.ModelForm):
    """Alta y edicion de un cliente."""

    class Meta:
        model = ClientModel
        fields = ('identification', 'full_name', 'email', 'phone', 'is_active')
        widgets = {
            'identification': forms.TextInput(
                attrs={'inputmode': 'numeric', 'autocomplete': 'off'}
            ),
            'full_name': forms.TextInput(attrs={'autocomplete': 'off'}),
        }

    def clean_identification(self) -> str:
        """
        Solo digitos, igual que en el portal.

        El modelo tambien lo normaliza al guardar, pero si el formulario no lo
        hiciera, la comprobacion de «ya existe ese cliente» se haria contra el
        texto con puntos y dejaria crear un duplicado.
        """
        raw = self.cleaned_data['identification']
        digits = ''.join(c for c in raw if c.isdigit())
        if not digits:
            raise forms.ValidationError(
                _('The identification must contain digits only.')
            )
        return digits


class CaseForm(BootstrapFormMixin, forms.ModelForm):
    """
    Alta y edicion de un asunto.

    Los tres bloques por tipo de tramite --judicial, administrativo y
    policivo-- se pintan todos y la plantilla los pliega; lo que decide cual
    vale es `CaseModel.clean()`, en el servidor. Esconderlos con JavaScript
    seria repetir el error de la pantalla anterior: lo que se esconde se
    sigue pudiendo mandar.
    """

    class Meta:
        model = CaseModel
        fields = (
            'client', 'service', 'procedure', 'area', 'subtype',
            'second_subtype', 'stage', 'instance', 'is_active',
            'case_number', 'court', 'city',
            'sector', 'entity', 'administrative_case_number',
            'administrative_city',
            'police_instance', 'police_office', 'police_case_number',
            'police_city',
            'paz_y_salvo_authorized',
        )


class CaseFinanceForm(BootstrapFormMixin, forms.ModelForm):
    """
    El dinero de un asunto.

    Cada modalidad usa columnas distintas y `CaseFinanceModel.clean()` rechaza
    las que no le tocan, asi que el formulario las ofrece todas y el servidor
    decide. El saldo no esta: se calcula.
    """

    class Meta:
        model = CaseFinanceModel
        fields = (
            'start_date', 'mandate', 'contingency_percentage',
            'contingency_value', 'agreed_fee', 'paid_amount',
            'show_in_dashboard',
        )
        widgets = {
            'start_date': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'
            ),
        }


#: El dinero va pegado a su asunto, igual que en el admin: un importe sin su
#: modalidad delante no se puede revisar. `max_num=1` porque la relacion es
#: uno a uno y el formset no deberia ofrecer un segundo.
CaseFinanceFormSet = inlineformset_factory(
    CaseModel,
    CaseFinanceModel,
    form=CaseFinanceForm,
    extra=1,
    max_num=1,
    can_delete=False,
)

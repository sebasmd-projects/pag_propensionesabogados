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

from . import choices
from .models import (CaseFinanceModel, CaseModel, CaseNoteModel,
                     ClientModel)

#: Lo que se contesta cuando esa identificacion no es de ningun cliente.
#:
#: Es distinto de «tu proceso esta inactivo» a proposito: alli el numero si es
#: de un cliente y lo que falta es vigencia. Aqui no hay a quien mandarle un
#: codigo, y decirlo es lo unico util --quien se equivoco de digito lo
#: corrige, y quien no es cliente se entera de que no lo es--.
UNKNOWN_IDENTIFICATION = _(
    'We could not find a case with that identification number.'
)

#: Cuando el cliente existe pero el despacho no tiene su correo.
#:
#: El codigo no se pierde: va a los buzones del despacho y se lo entregan
#: cuando llame. Lo que la pantalla tiene que decir es eso --que lo tiene la
#: oficina y a donde llamar-- y de paso que dejen registrado su correo, para
#: que la proxima vez le llegue directo.
NO_EMAIL_ON_FILE = _(
    'We do not have an email address on file for you, so we sent the access '
    'code to our offices. Please contact us to receive it, and we will '
    'register your email so it reaches you directly next time.'
)

#: Un codigo equivocado, caducado o tanteado dicen todos lo mismo.
INVALID_CODE = _('The code is not valid or has expired. Request a new one.')


class PublicCaseQueryForm(forms.Form):
    """
    El primer paso: solo la identificacion.

    Antes pedia tambien una «clave de acceso» que era la inicial del nombre
    mas los cuatro ultimos digitos de la cedula. Eso no acreditaba a nadie: se
    calcula con la cedula delante, y la cedula circula. Lo que acredita ahora
    es el codigo que llega al correo registrado, y eso es el segundo paso.
    """

    identification = forms.CharField(
        label=_('identification number'),
        max_length=20,
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
            raise forms.ValidationError(UNKNOWN_IDENTIFICATION)
        return digits

    def get_client(self) -> ClientModel | None:
        """
        El cliente de esa identificacion, exista o no.

        **Tambien devuelve a los que no estan vigentes**, y lo mira la vista:
        a quien tiene su proceso cerrado no se le contesta «no encontramos
        nada», porque se pondria a probar cedulas creyendo que se equivoco de
        numero. Se le manda su codigo igual y, cuando entra, la pantalla le
        dice que su proceso esta inactivo y a donde llamar.
        """
        return ClientModel.objects.filter(
            identification=self.cleaned_data['identification']
        ).first()


class PublicAccessCodeForm(forms.Form):
    """El segundo paso: las seis cifras que llegaron al correo."""

    code = forms.CharField(
        label=_('access code'),
        min_length=6,
        max_length=6,
    )

    def clean_code(self) -> str:
        digits = ''.join(
            character
            for character in (self.cleaned_data['code'] or '')
            if character.isdigit()
        )
        if len(digits) != 6:
            raise forms.ValidationError(INVALID_CODE)
        return digits

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

        if hasattr(self, "configure_fields"):
            self.configure_fields()

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

    Sigue servicio -> área/subnivel -> proceso. Los selectores anteriores
    se conservan como datos históricos, fuera del flujo de clasificación.
    """

    notify_stage_change = forms.BooleanField(
        label=_('Email the client if the stage changes'),
        required=False,
        help_text=_(
            'Only if the stage actually changes in this save, and only if the '
            'client has an email address on file.'
        ),
    )

    def configure_fields(self):
        def value(name):
            if self.is_bound:
                return self.data.get(self.add_prefix(name), '')
            return self.initial.get(name, '')

        service, area, subtype = value('service'), value('area'), value('subtype')
        for name in ('procedure', 'area', 'procedure_other', 'area_other'):
            self.fields[name].widget = forms.HiddenInput()
        self.fields['subtype'].label = (
            'Área' if service == choices.Service.JUDICIAL else 'Subnivel'
        )
        self.fields['second_subtype'].label = 'Tipo concreto de proceso'
        catalogs = {
            'subtype': choices.subtypes_for(service),
            'second_subtype': choices.second_subtypes_for(service, subtype),
            'instance': choices.instances_for(service),
        }
        # Lo que ya estaba guardado se sigue pudiendo guardar. Un expediente
        # anterior se clasifico con otro arbol, y si el formulario no le
        # ofreciera su propio valor, abrirlo y darle a guardar se lo cambiaria
        # sin que nadie lo pidiera. Solo el valor que tiene: no uno enviado.
        if service == self.instance.service:
            if subtype == self.instance.subtype and self.instance.second_subtype:
                catalogs['second_subtype'] = (
                    *catalogs['second_subtype'], self.instance.second_subtype
                )
            if self.instance.subtype:
                catalogs['subtype'] = (
                    *catalogs['subtype'], self.instance.subtype
                )
        if self.instance.instance:
            catalogs['instance'] = (*catalogs['instance'], self.instance.instance)
        for name, values in catalogs.items():
            self.fields[name] = forms.ChoiceField(
                label=self.fields[name].label, required=False,
                choices=[('', '---------'), *((v, v) for v in dict.fromkeys(values))],
            )

        for name in ('service', 'procedure', 'area', 'subtype', 'second_subtype'):
            field = self.fields[name + '_other']
            field.other_parent_id = self[name].id_for_label
            field.other_visible = choices.is_other(value(name))

    @property
    def classification_catalog(self):
        """
        El arbol que el navegador necesita para repintar los desplegables.

        Va entero y de una vez --son unas pocas decenas de cadenas-- porque la
        alternativa es una peticion al servidor por cada cambio de servicio,
        y quien esta capturando un expediente cambia de servicio mirando.

        Que aqui viaje el arbol **no** lo convierte en la fuente de la verdad:
        lo que se guarde lo vuelve a comprobar `CaseModel.clean()`. Esto solo
        decide que se ve.
        """
        return {
            'subtypes': {
                service: choices.subtypes_for(service)
                for service in choices.Service.values
            },
            'seconds': {
                service: {
                    subtype: choices.second_subtypes_for(service, subtype)
                    for subtype in branch
                }
                for service, branch in choices.CLASSIFICATION_TREE.items()
            },
            'instances': choices.INSTANCES_BY_SERVICE,
        }

    class Meta:
        model = CaseModel
        fields = (
            'client', 'service', 'procedure', 'area', 'subtype',
            'second_subtype', 'service_other', 'procedure_other', 'area_other',
            'subtype_other', 'second_subtype_other', 'stage', 'instance', 'is_active',
            'case_number', 'court', 'city',
            'sector', 'entity', 'administrative_case_number',
            'administrative_city',
            'police_instance', 'police_office', 'police_case_number',
            'police_city',
            'paz_y_salvo_authorized',
        )


class CaseNoteForm(BootstrapFormMixin, forms.ModelForm):
    """
    Una novedad del expediente, y si se le avisa al cliente.

    La casilla de aviso **no se guarda en la nota**: es una decision de este
    envio, no una propiedad de la novedad. Lo que si queda guardado es
    `notified_at`, que dice cuando se le aviso de verdad --y solo se rellena
    si el correo salio--.
    """

    notify_client = forms.BooleanField(
        label=_('Email this note to the client'),
        required=False,
        initial=True,
        help_text=_(
            'It goes out with the firm letterhead. Nothing is sent if the '
            'client has no email address on file.'
        ),
    )

    class Meta:
        model = CaseNoteModel
        fields = ('kind', 'title', 'body', 'visible_to_client')
        widgets = {
            'body': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Una nota que el cliente no ve tampoco se le manda por correo. Lo
        # decide `emails.send_case_note()`, pero decirlo aqui evita que
        # alguien marque las dos casillas y espere un envio que no llega.
        self.fields['visible_to_client'].help_text = _(
            'If this is off, the note stays in the file and no email is sent.'
        )


class CaseFinanceForm(BootstrapFormMixin, forms.ModelForm):
    """
    El dinero de un asunto.

    Cada modalidad muestra sus columnas; el modelo valida los importes.
    """

    def configure_fields(self):
        mandate = (
            self.data.get(self.add_prefix('mandate'))
            if self.is_bound else self.initial.get('mandate')
        )
        self.is_free = mandate in (
            choices.Mandate.PRO_BONO, choices.Mandate.GUARDIANSHIP,
        )
        percentage = (
            self.data.get(self.add_prefix('contingency_percentage'), '0')
            if self.is_bound else self.initial.get('contingency_percentage', 0)
        )
        litis = mandate == choices.Mandate.CONTINGENCY
        payment = mandate == choices.Mandate.PAYMENT
        for name, visible in {
            'contingency_percentage': litis,
            'contingency_value': litis,
            'agreed_fee': payment,
            'paid_amount': payment or (litis and str(percentage) == '0'),
            'show_in_dashboard': not self.is_free,
        }.items():
            self.fields[name].flow_hidden = not visible
        if self.is_bound and self.is_free:
            # Las modalidades gratuitas no reciben cifras, incluso sin JS
            # o al cambiar desde un contrato con importes anteriores.
            for name in ('contingency_percentage', 'contingency_value',
                         'agreed_fee', 'paid_amount'):
                self.fields[name].disabled = True
                self.initial[name] = 0

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

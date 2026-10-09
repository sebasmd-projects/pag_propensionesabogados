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

import json
from datetime import date

from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from . import choices
from .identification import nit_check_digit, normalize_number, split_lookup
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
        label=_('ID number, NIT or document'),
        max_length=40,
    )

    verification_digit = ''

    def clean_identification(self) -> str:
        """
        Normaliza: sin puntos, espacios ni `-DV`.

        Quien escribe su cedula con puntos esta escribiendo la misma cedula, y
        el campo de la base esta normalizado. Un NIT se acepta con o sin
        digito de verificacion (`900123456`, `900.123.456-7`); el DV, si viene,
        se guarda aparte para comprobarlo en `get_client`.
        """
        number, dv = split_lookup(self.cleaned_data['identification'])
        if not number:
            raise forms.ValidationError(UNKNOWN_IDENTIFICATION)
        self.verification_digit = dv
        return number

    def get_client(self) -> ClientModel | None:
        """
        El cliente de esa identificacion, exista o no.

        **Tambien devuelve a los que no estan vigentes**, y lo mira la vista:
        a quien tiene su proceso cerrado no se le contesta «no encontramos
        nada», porque se pondria a probar cedulas creyendo que se equivoco de
        numero. Se le manda su codigo igual y, cuando entra, la pantalla le
        dice que su proceso esta inactivo y a donde llamar.
        """
        client = ClientModel.objects.filter(
            identification=self.cleaned_data['identification']
        ).first()
        if client is None or not self.verification_digit:
            return client

        # Si vino con DV tiene que ser el de un NIT y cuadrar. Un DV que no
        # cuadra responde exactamente lo mismo que un documento inexistente:
        # de otro modo el portal diria «ese numero existe, pero el DV no».
        if (
            not client.is_nit
            or client.verification_digit != self.verification_digit
            or nit_check_digit(client.identification)
            != self.verification_digit
        ):
            return None
        return client


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
        fields = (
            'identification_type', 'identification', 'verification_digit',
            'full_name', 'email', 'phone',
            'legal_rep_name', 'legal_rep_identification_type',
            'legal_rep_identification', 'legal_rep_email', 'legal_rep_phone',
            'is_active',
        )
        widgets = {
            'identification': forms.TextInput(
                attrs={'autocomplete': 'off', 'data-client-id-number': ''}
            ),
            'verification_digit': forms.TextInput(
                attrs={'inputmode': 'numeric', 'maxlength': '1',
                       'autocomplete': 'off'}
            ),
            'full_name': forms.TextInput(attrs={'autocomplete': 'off'}),
            'legal_rep_name': forms.TextInput(attrs={'autocomplete': 'off'}),
            'legal_rep_identification': forms.TextInput(
                attrs={'autocomplete': 'off'}
            ),
            'legal_rep_phone': forms.TextInput(attrs={'autocomplete': 'off'}),
        }

    #: Los campos que solo existen con NIT: el JS los oculta y deshabilita.
    NIT_ONLY = (
        'verification_digit', 'legal_rep_name',
        'legal_rep_identification_type', 'legal_rep_identification',
        'legal_rep_email', 'legal_rep_phone',
    )

    def configure_fields(self):
        # Un envio sin tipo (un script, un formulario viejo) es un CC, que es
        # lo que eran todos hasta ahora; el selector del gestor siempre lo manda.
        self.fields['identification_type'].required = False
        self.fields['identification'].label = _('Document number')
        self.fields['verification_digit'].label = _('Check digit (DV)')
        self.fields['full_name'].label = (
            _('Company name') if self._is_nit() else _('Full name')
        )
        self.fields['full_name'].widget.attrs['data-label-person'] = _('Full name')
        self.fields['full_name'].widget.attrs['data-label-company'] = _('Company name')
        self.fields['legal_rep_name'].label = _('Name')
        self.fields['legal_rep_identification_type'].label = _('Document type')
        self.fields['legal_rep_identification'].label = _('Document number')
        self.fields['legal_rep_email'].label = _('Email')
        self.fields['legal_rep_phone'].label = _('Phone')

    def _is_nit(self) -> bool:
        if self.is_bound:
            value = self.data.get(self.add_prefix('identification_type'))
        else:
            value = self.initial.get(
                'identification_type', self.instance.identification_type
            )
        return value == choices.IdentificationType.NIT

    @property
    def show_nit_fields(self) -> bool:
        """Se pintan visibles si es NIT o si hay un error en ellos."""
        return self._is_nit() or any(
            name in self.errors for name in self.NIT_ONLY
        )

    def clean_identification_type(self) -> str:
        return (
            self.cleaned_data.get('identification_type')
            or self.instance.identification_type
            or choices.IdentificationType.CC
        )

    def clean_identification(self) -> str:
        """
        Sin puntos, espacios ni guiones, igual que en el portal.

        El modelo tambien lo normaliza al guardar, pero si el formulario no lo
        hiciera, la comprobacion de «ya existe ese cliente» se haria contra el
        texto con puntos y dejaria crear un duplicado. Que sean digitos (o
        letras, en un pasaporte) lo decide `ClientModel.clean()` segun el
        tipo.
        """
        id_type = self.cleaned_data.get('identification_type') or choices.IdentificationType.CC
        number = normalize_number(self.cleaned_data['identification'], id_type)
        if not number:
            raise forms.ValidationError(
                _('The identification must contain digits only.')
            )
        self.deleted_client = ClientModel.all_objects.filter(
            identification=number, deleted_at__isnull=False,
        ).exclude(pk=self.instance.pk).first()
        if self.deleted_client:
            raise forms.ValidationError(_(
                'Existe un cliente eliminado con ese documento. Puedes restaurarlo.'
            ))
        return number

    def clean_verification_digit(self) -> str:
        return (self.cleaned_data.get('verification_digit') or '').strip()

    def clean_legal_rep_identification(self) -> str:
        rep_type = self.cleaned_data.get('legal_rep_identification_type') or ''
        return normalize_number(
            self.cleaned_data.get('legal_rep_identification'),
            rep_type or choices.IdentificationType.CC,
        )


class CaseForm(BootstrapFormMixin, forms.ModelForm):
    """
    Alta y edicion de un asunto.

    Sigue servicio -> área/subnivel -> proceso. Los selectores anteriores
    se conservan como datos históricos, fuera del flujo de clasificación.
    """

    confirm_duplicate = forms.BooleanField(required=False, widget=forms.HiddenInput)
    duplicate_case = None

    def clean(self):
        data = super().clean()
        watched = ('client', 'service', 'subtype', 'case_number',
                   'administrative_case_number', 'police_case_number')
        if not self.instance._state.adding and not any(
            name in self.changed_data for name in watched
        ):
            return data
        if not data.get('client') or not data.get('service'):
            return data
        def normalize(value):
            return ''.join((value or '').split()).replace('-', '').upper()
        reference = next((data.get(name) for name in watched[3:] if data.get(name)), '')
        candidates = CaseModel.objects.filter(
            client=data['client'], service=data['service'],
        ).exclude(pk=self.instance.pk)
        subtype = data.get('subtype') or ''
        candidates = candidates.filter(subtype=subtype) if subtype else candidates.filter(
            Q(subtype='') | Q(subtype__isnull=True)
        )
        for case in candidates:
            existing = case.case_number or case.administrative_case_number or case.police_case_number
            if not reference or normalize(reference) == normalize(existing):
                self.duplicate_case = case
                break
        if self.duplicate_case and not data.get('confirm_duplicate'):
            if reference:
                message = _('El servicio «%(service)s» con radicado «%(reference)s» ya existe para este cliente. ¿Deseas continuar?') % {
                    'service': data['service'], 'reference': reference,
                }
            else:
                message = _('El servicio «%(service)s» ya existe para este cliente. ¿Deseas continuar?') % {'service': data['service']}
            raise forms.ValidationError(message)
        return data

    notify_stage_change = forms.BooleanField(
        label=_('Email the client if the stage changes'),
        required=False,
        help_text=_(
            'Only if the stage actually changes in this save, and only if the '
            'client has an email address on file.'
        ),
    )

    def configure_fields(self):
        if not self.is_bound and not self.instance._state.adding:
            service, subtype, second = choices.restore_classification(
                self.instance.service, self.instance.subtype, self.instance.second_subtype,
            )
            self.initial.update(service=service, subtype=subtype, second_subtype=second)

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
        if service == self.instance.service and self.instance.instance:
            catalogs['instance'] = (*catalogs['instance'], self.instance.instance)
        for name, values in catalogs.items():
            self.fields[name] = forms.ChoiceField(
                label=self.fields[name].label, required=False,
                choices=[('', '---------'), *((v, v) for v in dict.fromkeys(values))],
            )

        # La primera respuesta HTML debe respetar las mismas dependencias
        # que el navegador, sin mostrar brevemente todos los campos.
        for name in ('subtype', 'second_subtype', 'instance'):
            self.fields[name].flow_hidden = not (
                catalogs[name] and (name != 'subtype' or service != choices.Service.OTHER)
            )
        self.fields['court'].flow_hidden = service != choices.Service.JUDICIAL
        self.fields['city'].label = (
            'Ciudad del proceso' if service == choices.Service.JUDICIAL
            else 'Ciudad / municipio (opcional)'
        )
        self.fields['case_number'].label = 'Número de radicado / referencia (opcional)'
        self.details_title = (
            'Representación judicial' if service == choices.Service.JUDICIAL
            else 'Datos del proceso'
        )
        self.show_administrative = value('procedure') == choices.Procedure.ADMINISTRATIVE or any(
            value(name) for name in ('sector', 'entity', 'administrative_case_number', 'administrative_city')
        )
        self.show_police = value('procedure') == choices.Procedure.POLICE or any(
            value(name) for name in ('police_instance', 'police_office', 'police_case_number', 'police_city')
        )

        for name in ('service', 'procedure', 'area', 'subtype', 'second_subtype'):
            field = self.fields[name + '_other']
            field.other_parent_id = self[name].id_for_label
            field.other_visible = (
                choices.is_other(value(name))
                and not getattr(self.fields[name], 'flow_hidden', False)
            )

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

    Cada esquema de honorarios muestra sus columnas; el modelo valida los importes.
    """

    def configure_fields(self):
        self.fields['mandate'].choices = [
            ('', 'Seleccione un esquema de honorarios'),
            (choices.Mandate.CONTINGENCY.value, choices.Mandate.CONTINGENCY.label),
            (choices.Mandate.PAYMENT.value, choices.Mandate.PAYMENT.label),
            (choices.Mandate.PRO_BONO.value, choices.Mandate.PRO_BONO.label),
            (choices.Mandate.GUARDIANSHIP.value, choices.Mandate.GUARDIANSHIP.label),
        ]
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
        self.is_payment = payment
        self.initial['payment_history'] = self.instance.payment_history or (
            [{'kind': 'payment', 'amount': self.instance.paid_amount,
              'date': '', 'next_date': '', 'legacy': True}]
            if self.instance.paid_amount and self.instance.mandate == choices.Mandate.PAYMENT
            else []
        )
        if self.is_bound and not payment:
            self.fields['payment_history'].disabled = True
        if self.is_bound and payment and self.add_prefix('payment_history') in self.data:
            self.fields['paid_amount'].disabled = True
            self.initial['paid_amount'] = 0
        for name, visible in {
            'contingency_percentage': litis,
            'contingency_value': litis,
            'agreed_fee': payment,
            'paid_amount': litis and str(percentage) == '0',
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

    @property
    def payment_rows(self):
        raw = self['payment_history'].value()
        try:
            rows = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            rows = []
        rows = [r for r in (rows or []) if isinstance(r, dict)] if isinstance(rows, list) else []
        admin = next((r for r in rows if r.get('kind') == 'administrative'), None)
        payments = [r for r in rows if r.get('kind') in ('payment', 'expected')]
        return [admin or {'kind': 'administrative', 'amount': 0},
                *(payments or [{'kind': 'payment', 'amount': 0}])]

    def clean_payment_history(self):
        rows = self.cleaned_data.get('payment_history') or []
        if not self.is_payment:
            return self.instance.payment_history
        if not isinstance(rows, list) or len(rows) > 100:
            raise forms.ValidationError('El historial admite hasta 100 pagos.')
        result = []
        admin_count = 0
        old_rows = self.initial.get('payment_history', [])
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or row.get('kind') not in ('administrative', 'payment', 'expected'):
                raise forms.ValidationError('Tipo de pago inválido.')
            amount = row.get('amount', 0)
            if type(amount) is not int or not 0 <= amount <= 9_000_000_000_000:
                raise forms.ValidationError('Cada pago debe ser un valor entero no negativo.')
            if row['kind'] == 'expected' and amount == 0:
                raise forms.ValidationError('El valor esperado debe ser mayor que cero.')
            admin_count += row['kind'] == 'administrative'
            if admin_count > 1:
                raise forms.ValidationError('Solo puede existir un pago administrativo.')
            dates = {}
            for key in ('date', 'next_date'):
                value = row.get(key) or ''
                try:
                    dates[key] = date.fromisoformat(value).isoformat() if value else ''
                except (TypeError, ValueError):
                    raise forms.ValidationError(f'Fecha inválida en el pago {index + 1}.')
            legacy = (index < len(old_rows) and old_rows[index].get('legacy')
                      and old_rows[index].get('amount') == amount
                      and old_rows[index].get('kind') == row['kind'])
            # La interfaz agrega al inicio la fila administrativa a los abonos importados.
            if not legacy and index == 1 and len(old_rows) == 1:
                legacy = (old_rows[0].get('legacy') and old_rows[0].get('amount') == amount
                          and row['kind'] == 'payment')
            # La fecha no se exige. Un abono se registra muchas veces antes de
            # tener el comprobante delante --el cliente avisa por telefono y el
            # papel llega dias despues-- y obligar a inventarse una fecha para
            # poder guardar el importe es peor que guardarlo sin ella: la
            # inventada parece un dato y la que falta se ve que falta.
            if dates['date'] and dates['next_date'] and dates['next_date'] < dates['date']:
                raise forms.ValidationError('La próxima fecha de pago no puede ser anterior al pago.')
            result.append({'kind': row['kind'], 'amount': amount, **dates,
                           'legacy': bool(legacy and not dates['date'])})
        return result

    def clean(self):
        data = super().clean()
        if self.is_payment and 'payment_history' in data:
            if self.add_prefix('payment_history') in self.data or self.instance.payment_history:
                if self.add_prefix('payment_history') not in self.data:
                    data['payment_history'] = self.instance.payment_history
                data['paid_amount'] = sum(row['amount'] for row in data['payment_history']
                                          if row['kind'] != 'expected')
        return data

    class Meta:
        model = CaseFinanceModel
        fields = (
            'start_date', 'mandate', 'contingency_percentage',
            'contingency_value', 'agreed_fee', 'paid_amount',
            'show_in_dashboard',
            'payment_history',
        )
        widgets = {
            # `data-money` solo pide formato visual COP en el navegador; el
            # valor enviado sigue siendo el entero sin puntos ni simbolo.
            'contingency_value': forms.NumberInput(attrs={'data-money': ''}),
            'agreed_fee': forms.NumberInput(attrs={'data-money': ''}),
            'paid_amount': forms.NumberInput(attrs={'data-money': ''}),
            'payment_history': forms.HiddenInput(),
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

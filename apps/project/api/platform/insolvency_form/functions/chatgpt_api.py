#  apps/project/api/platform/insolvency_form/functions/chatgpt_api.py

from django.conf import settings
from openai import OpenAI


class ChatGPTAPI:
    def __init__(self):
        self.client = OpenAI(api_key=settings.CHAT_GPT_API_KEY)

    def debtor_cessation_report_prompt(self, user_text):
        prompt = f"""
        Eres un asistente jurídico para Colombia en una firma de abogados.
        Tienes un párrafo de un cliente con su descripción de hechos:
        \"\"\"{user_text}\"\"\"

        Reescribe ese texto como una declaración jurídica coherente y cohesionada:
        - Sólo usa la información existente, no inventes nada.
        - No incluyas referencias a leyes o artículos.
        - Sustituye verbos genéricos por términos jurídicos.
        - Convierte situaciones personales en categorías legales.
        - Prioriza causalidad demostrable.
        - Mantén texto corrido, bien estructurado.
        
        Causas legales de insolvencia:
        - Pérdida de empleo o disminución sustancial de ingresos
        - Enfermedades graves, tratamientos médicos costosos o discapacidad
        - Dependencia económica de familiares o personas a cargo
        - Endeudamiento excesivo por crédito de consumo, libranzas o tarjetas
        - Eventos fortuitos o de fuerza mayor (desastres naturales, robos, pandemias)
        - Negocios fallidos o pérdidas patrimoniales
        - Embargos, secuestros de cuentas o descuentos por libranza desproporcionados
        - Fallecimiento de un aportante del hogar
        - Desempleo prolongado del deudor o del cónyuge
        - Alteración severa en la economía del país o del sector donde trabaja
        - Pérdida o reducción del contrato de prestación de servicios
        - Incremento desproporcionado en el costo de vida (inflación, servicios, arriendo)
        - Errores en la estructuración de los créditos otorgados (sobreendeudamiento inducido)
        - Separación o ruptura conyugal que afectó la economía del hogar
        - Pago simultáneo de cuotas hipotecarias y otras obligaciones conyugales
        - Carga financiera por estudios o educación de hijos
        - Incumplimientos contractuales de terceros que afectaron el flujo de caja del deudor

        Devuélmelo como un párrafo.
        """

        messages = [
            {"role": "system", "content": "Eres un transformador de texto legal."},
            {"role": "user", "content": prompt}
        ]

        model = "gpt-4o"

        return messages, model

    def creditor_nit_contact_prompt(self, creditor_name):
        prompt = f"""
        Eres un asistente jurídico colombiano.
        Cuando se te pida 'Dame el NIT y el correo de contacto de X',
        respondes únicamente un JSON con las claves
        'nit' y 'contact', sin explicaciones de esa empresa o entidad.
        el json debe ser plano sin ```json...``` solo las llaves.
        En el correo de contacto, si encuentras el correo de notificaciones judiciales, agrega ese,
        de lo contrario, agrega el correo de contacto general.
        Para los siguientes bancos utiliza el correo de notificaciones judiciales:
        Bancolombia: notificacijudicial@bancolombia.com.co
        Banco de Bogotá: rjudicial@bancodebogota.com.co
        Banco Davivienda: notificacionesjudiciales@davivienda.com
        Banco Popular: notificacionesjudicialesvjuridica@bancopopular.com.co
        Banco BBVA: notifica.co@bbva.com
        Banco AV Villas: notificacionesjudiciales@bancoavvillas.com.co
        Banco Itaú: notificaciones.juridico@itau.co
        Banco Colpatria: notificbancolpatria@scotiabankcolpatria.com
        Banco BCSC: notificacionesjudiciales@fundaciongruposocial.co
        Banco Citibank: legalnotificacionescitibank@citi.com.co
        Banco Agrario de Colombia: notificacionesjudiciales@bancoagrario.gov.co
        """

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Dame el NIT y el correo de contacto de {creditor_name}."}
        ]

        model = "gpt-4o-mini"

        return messages, model

    def get_response(self, model, messages):
        response = self.client.chat.completions.create(
            model=model,
            temperature=0,
            messages=messages
        )
        polished = response.choices[0].message.content.strip()
        return polished

    def get_response_json(self, model, messages):
        response = self.client.chat.completions.create(
            model=model,
            temperature=0,
            messages=messages,
            response_format={"type": "json_object"}
        )
        polished = response.choices[0].message.content.strip()
        return polished

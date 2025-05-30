#  apps/project/api/platform/insolvency_form/api/views.py

from .serializers import SignatureCreateSerializer
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import (AuthenticationFailed,
                                       NotFound)
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.utils.functions import verify_token
from apps.project.api.platform.auth_platform.api.views import \
    AttlasInsolvencyAuthModel

from ..functions import ChatGPTAPI
from ..models import AttlasInsolvencyFormModel, AttlasInsolvencySignatureModel
from .serializers import (Step1Serializer, Step2Serializer, Step3Serializer,
                          Step4Serializer, Step5Serializer, Step6Serializer,
                          Step7Serializer, Step8Serializer, Step9Serializer,
                          Step10Serializer, Step11Serializer)

logger = logging.getLogger(__name__)

STEP_SERIALIZERS = {
    '1': Step1Serializer,
    '2': Step2Serializer,
    '3': Step3Serializer,
    '4': Step4Serializer,
    '5': Step5Serializer,
    '6': Step6Serializer,
    '7': Step7Serializer,
    '8': Step8Serializer,
    '9': Step9Serializer,
    '10': Step10Serializer,
    '11': Step11Serializer,
}


class BearerTokenAuthentication:
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        try:
            user_id = verify_token(token)
            user = AttlasInsolvencyAuthModel.objects.get(id=user_id)
            return (user, None)
        except Exception as e:
            raise AuthenticationFailed(str(e))

    def authenticate_header(self, request):
        return 'Bearer'


class InsolvencyFormWizardView(RetrieveUpdateAPIView):
    """
    GET  /api/v1/insolvency-form/<id>/?step=N
    PATCH /api/v1/insolvency-form/<id>/?step=N
    """
    queryset = AttlasInsolvencyFormModel.objects.all().select_related('user').prefetch_related(
        'creditors_form',
        'asset_form',
        'judicial_form',
        'incomes__incomeother_income',
        'resources__tables__items'
    )
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_serializer_class(self):
        step = self.request.query_params.get('step', '1')
        return STEP_SERIALIZERS.get(step, Step1Serializer)

    def retrieve(self, request, *args, **kwargs):
        """
        En el GET, además de lo que devuelva el serializer,
        añadimos siempre el flag `is_completed`.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        data['is_completed'] = instance.is_completed
        return Response(data)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        step = request.query_params.get('step', '1')

        # 1) Validar que `step` sea numérico y no se salte pasos
        try:
            si = int(step)
        except ValueError:
            return Response(
                {"detail": "step debe ser numérico"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if si > instance.current_step + 1:
            return Response(
                {"detail": "No puede saltar pasos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2) Serializar y post-procesar si es paso 4
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        # 3) Guardado con posible transformación de ChatGPT
        self.perform_update(serializer, step)

        # 4) Avanzar current_step / is_completed
        if si < len(STEP_SERIALIZERS):
            instance.current_step = max(instance.current_step, si + 1)
        else:
            instance.is_completed = True
        instance.save()

        # 5) Devolver datos actualizados
        return Response(self.get_serializer(instance).data)


    def debtor_cessation_report_prompt(self, user_text):
        prompt = f"""
        Eres un asistente jurídico experto en insolvencia para Colombia, 
        trabajando en una firma de abogados especializada en proteger los derechos y la dignidad de las personas endeudadas.
        
        Tienes frente a ti un relato escrito por un cliente:
        \"\"\"{user_text}\"\"\"

        Tu tarea es transformarlo en una declaración jurídica bien estructurada, 
        que exprese de forma conmovedora, humana y comprensible las causas que llevaron al estado de insolvencia.

        Ten en cuenta:
        - No inventes información ni agregues hechos que no estén en el texto original.
        - Usa términos jurídicos precisos para sustituir verbos o frases genéricas.
        - Resalta las categorías legales que aplican (sin enumerarlas explícitamente).
        - Identifica claramente la relación causa-efecto entre los hechos narrados y la incapacidad de pago.
        - Usa un lenguaje emotivo pero profesional, que refleje el sufrimiento humano detrás de los hechos.
        - No incluyas referencias a leyes, artículos ni normas.
        - Mantén la coherencia, fluidez y conexión entre ideas.
        - Escribe en texto corrido pero con parrafos, sin listas, manteniendo un tono serio, empático y creíble.
        
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
        
        Recuerda: el resultado debe sonar más elaborado y profundo, 
        reflejando la lucha, las dificultades y la esperanza de la persona,
        sin cambiar el fondo de lo relatado ni exagerar los hechos.
        """

        messages = [
            {"role": "system", "content": "Eres un transformador de texto legal, capaz de redactar declaraciones conmovedoras, humanas y bien argumentadas."},
            {"role": "user", "content": prompt}
        ]

        model = "gpt-4o"
        temperature = 0.6

        return messages, model, temperature


    def perform_update(self, serializer, step):
        """
        Si estamos en el paso 4 y llegó debtor_cessation_report,
        lo enviamos a ChatGPTAPI para pulirlo antes de guardar.
        """
        save_kwargs = {'user': self.request.user}

        if step == '4':
            data = serializer.validated_data
            raw_report = data.get('debtor_cessation_report', '').strip()
            use_ai = data.pop('use_ai', True)

            if raw_report and use_ai:
                try:
                    api = ChatGPTAPI()
                    msgs, model, temperature = self.debtor_cessation_report_prompt(raw_report)
                    polished = api.get_response(model=model, messages=msgs, temperature=temperature)
                    save_kwargs['debtor_cessation_report'] = polished
                except Exception as e:
                    logger.error(
                        "Error usando IA en paso 4: %s", str(e), exc_info=True
                    )
                    save_kwargs['debtor_cessation_report'] = raw_report
            else:
                save_kwargs['debtor_cessation_report'] = raw_report

        serializer.save(**save_kwargs)

    def get_object(self):
        """
        Si la URL trae <id>, usamos el comportamiento normal (retrieve/update
        sobre ese objeto).  Si es la ruta /insolvency-form/ simplemente
        buscamos (o creamos) el formulario del usuario autenticado.
        """
        if 'id' in self.kwargs:
            return super().get_object()

        form, _ = AttlasInsolvencyFormModel.objects.get_or_create(
            user=self.request.user,
            defaults={"current_step": 1}
        )
        return form


class SignatureUpdateView(RetrieveUpdateAPIView):
    """
    GET  /api/v1/insolvency-form/signature/<id>/
    PATCH /api/v1/insolvency-form/signature/<id>/
    """
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = Step11Serializer
    lookup_field = 'id'   # o usa 'id' y adapta los kwargs

    def get_object(self):
        # 1. Verificar que el formulario existe y está completado
        try:
            form = AttlasInsolvencyFormModel.objects.get(id=self.kwargs['id'])
        except AttlasInsolvencyFormModel.DoesNotExist:
            raise NotFound("El formulario no existe.")

        # 2. Obtener el objeto de firma o crear uno nuevo
        signature, _ = AttlasInsolvencySignatureModel.objects.get_or_create(
            form=form
        )
        return signature


class SignatureCreateAPIView(CreateAPIView):
    """
    POST /api/platform/signature/
    {
      "cedula": "0000000000",
      "signature": "<base64string>"
    }
    """
    serializer_class = SignatureCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        # Validar y guardar
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sig_obj = serializer.save()
        # Devolver sólo el payload de to_representation()
        return Response(serializer.to_representation(sig_obj), status=status.HTTP_200_OK)

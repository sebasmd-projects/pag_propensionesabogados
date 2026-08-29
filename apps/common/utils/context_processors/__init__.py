from typing import Any

from django.utils.translation import gettext_lazy as _


def custom_processors(request: Any) -> dict[str, Any]:
    PRACTICE_AREAS: Any = [
        {
            "image_en": "pensiones_negadas_en.webp",
            "image_es": "pensiones_negadas_es.webp",
            "subject": _("Denied Pensions"),
            "alt": _("Denied Pensions"),
        },
        {
            "image_en": "insolvencia_economica_en.webp",
            "image_es": "insolvencia_economica_es.webp",
            "subject": _("Economic Insolvency"),
            "alt": _("Economic Insolvency"),
        },
        {
            "image_en": "derecho_laboral_en.webp",
            "image_es": "derecho_laboral_es.webp",
            "subject": _("Labor Law"),
            "alt": _("Labor Law"),
        },
        {
            "image_en": "derecho_civil_en.webp",
            "image_es": "derecho_civil_es.webp",
            "subject": _("Civil Law"),
            "alt": _("Civil Law"),
        },
        {
            "image_en": "derecho_penal_en.webp",
            "image_es": "derecho_penal_es.webp",
            "subject": _("Criminal Law"),
            "alt": _("Criminal Law"),
        },
        {
            "image_en": "derecho_internacional_en.webp",
            "image_es": "derecho_internacional_es.webp",
            "subject": _("International Law"),
            "alt": _("International Law"),
        },
        {
            "image_en": "analisis_de_riesgos_en.webp",
            "image_es": "analisis_de_riesgos_es.webp",
            "subject": _("Risk Analysis"),
            "alt": _("Risk Analysis"),
        },
        {
            "image_en": "capacitacion_empresarial_en.webp",
            "image_es": "capacitacion_empresarial_es.webp",
            "subject": _("Business Training"),
            "alt": _("Business Training"),
        },
        {
            "image_en": "conciliaciones_de_emergencia_en.webp",
            "image_es": "conciliaciones_de_emergencia_es.webp",
            "subject": _("Emergency Conciliation"),
            "alt": _("Emergency Conciliation"),
        },
        {
            "image_en": "consultoria_empresarial_en.webp",
            "image_es": "consultoria_empresarial_es.webp",
            "subject": _("Business Consulting"),
            "alt": _("Business Consulting"),
        },
        {
            "image_en": "derecho_de_familia_en.webp",
            "image_es": "derecho_de_familia_es.webp",
            "subject": _("Family Law"),
            "alt": _("Family Law"),
        },
        {
            "image_en": "investigacion_de_campo_en.webp",
            "image_es": "investigacion_de_campo_es.webp",
            "subject": _("Field Investigation"),
            "alt": _("Field Investigation"),
        },

    ]

    ctx: dict[str, Any] = {}

    ctx["PRACTICE_AREAS"] = PRACTICE_AREAS

    return ctx

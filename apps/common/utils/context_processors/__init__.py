from typing import Any

from django.utils.translation import gettext_lazy as _


def custom_processors(request: Any) -> dict[str, Any]:
    PRACTICE_AREAS: list[dict[str, str]] = [
        {
            "image": "analisis_de_riesgos.webp",
            "subject": _("Risk Analysis"),
            "alt": _("Risk Analysis"),
        },
        {
            "image": "capacitacion_empresarial.webp",
            "subject": _("Business Training"),
            "alt": _("Business Training"),
        },
        {
            "image": "conciliaciones_de_emergencia.webp",
            "subject": _("Emergency Conciliation"),
            "alt": _("Emergency Conciliation"),
        },
        {
            "image": "consultoria_empresarial.webp",
            "subject": _("Business Consulting"),
            "alt": _("Business Consulting"),
        },
        {
            "image": "departamento_juridico.webp",
            "subject": _("Legal Department"),
            "alt": _("Legal Department"),
        },
        {
            "image": "derecho_civil.webp",
            "subject": _("Civil Law"),
            "alt": _("Civil Law"),
        },
        {
            "image": "derecho_de_familia.webp",
            "subject": _("Family Law"),
            "alt": _("Family Law"),
        },
        {
            "image": "derecho_internacional.webp",
            "subject": _("International Law"),
            "alt": _("International Law"),
        },
        {
            "image": "derecho_laboral.webp",
            "subject": _("Labor Law"),
            "alt": _("Labor Law"),
        },
        {
            "image": "derecho_penal.webp",
            "subject": _("Criminal Law"),
            "alt": _("Criminal Law"),
        },
        {
            "image": "insolvencia_economica.webp",
            "subject": _("Economic Insolvency"),
            "alt": _("Economic Insolvency"),
        },
        {
            "image": "investigacion_de_campo.webp",
            "subject": _("Field Investigation"),
            "alt": _("Field Investigation"),
        },
        {
            "image": "pensiones_negadas.webp",
            "subject": _("Denied Pensions"),
            "alt": _("Denied Pensions"),
        },
    ]

    ctx: dict[str, Any] = {}

    ctx["PRACTICE_AREAS"] = PRACTICE_AREAS

    return ctx

import re
from datetime import datetime

from django.contrib import admin
from django.db.models import Q
from django.utils.dateparse import parse_date

from .models import AttlasInsolvencyAuthModel, AttlasInsolvencyAuthConsultantsModel, hash_value


CEDULA_PATTERN = re.compile(r'^\d{5,}$')


@admin.register(AttlasInsolvencyAuthModel)
class AttlasInsolvencyAuthAdminModel(admin.ModelAdmin):
    # ───────── Visualización ─────────
    list_display = ['document_number', 'birth_date', 'created', 'updated']
    readonly_fields = ['document_number_hash', 'birth_date_hash']
    list_filter = ['created']
    ordering = ['-created']

    # search_fields queda opcional; lo mantenemos para reutilizar la lógica por defecto.
    # No funcionará solo, pero no estorba y mantiene búsquedas sobre PK/UUID si las necesitas.
    search_fields = ['id']

    # ───────── Búsqueda extendida ─────────
    def get_search_results(self, request, queryset, search_term):
        """
        Permite escribir la cédula o la fecha (AAAA-MM-DD) “en claro”
        y buscar contra los hashes almacenados.
        """
        # primero aprovecha los filtros estándar por si el usuario escribe un UUID
        qs, use_distinct = super().get_search_results(request, queryset, search_term)

        # 1) Búsqueda por cédula
        # quita puntos/comas/espacios
        cleaned = re.sub(r'\D', '', search_term)
        if CEDULA_PATTERN.match(cleaned):
            qs |= self.model.objects.filter(
                document_number_hash=hash_value(cleaned)
            )

        # 2) Búsqueda por fecha de nacimiento (AAAA-MM-DD o DD/MM/AAAA)
        date_obj = parse_date(search_term)
        if not date_obj:
            try:
                date_obj = datetime.strptime(search_term, '%d/%m/%Y').date()
            except ValueError:
                date_obj = None

        if date_obj:
            qs |= self.model.objects.filter(
                birth_date_hash=hash_value(date_obj.strftime('%Y-%m-%d'))
            )

        return qs, use_distinct


@admin.register(AttlasInsolvencyAuthConsultantsModel)
class AttlasInsolvencyAuthConsultantsAdminModel(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'user', 'created', 'updated']
    list_display_links = list_display[:3]
    search_fields = ['first_name', 'last_name', 'user']
    readonly_fields = ['updated', 'created', 'user']

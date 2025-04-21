from django.contrib import admin

from .models import AttlasInsolvencyAuthModel, AttlasInsolvencyAuthConsultantsModel


@admin.register(AttlasInsolvencyAuthModel)
class AttlasInsolvencyAuthAdminModel(admin.ModelAdmin):
    list_display = ['document_number', 'birth_date', 'created', 'updated']
    search_fields = ['document_number', 'birth_date']
    readonly_fields = ['document_number_hash', 'birth_date_hash']
    
@admin.register(AttlasInsolvencyAuthConsultantsModel)
class AttlasInsolvencyAuthConsultantsAdminModel(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'user', 'created', 'updated']
    list_display_links = list_display[:3]
    search_fields = ['first_name', 'last_name', 'user']
    readonly_fields = ['updated', 'created', 'user']
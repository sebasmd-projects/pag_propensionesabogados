from django.contrib import admin

from .models import AttlasInsolvencyAuthModel


@admin.register(AttlasInsolvencyAuthModel)
class AttlasInsolvencyAuthAdminModel(admin.ModelAdmin):
    list_display = ['document_number', 'document_issue_date', 'birth_date']
    search_fields = ['document_number', 'document_issue_date', 'birth_date']
    readonly_fields = ['document_number_hash', 'document_issue_date_hash', 'birth_date_hash']

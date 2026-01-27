# apps/common/core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import ContactModel, ModalBannerModel, TeamMemberModel


@admin.register(ContactModel)
class ContactModelAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'last_name', 'email',
        'subject', 'created',
        'state'
    )
    list_display_links = ('name', 'last_name', 'email')
    search_fields = ('name', 'last_name', 'email', 'subject', 'message')
    list_filter = ('is_active', 'state')
    ordering = ('-created',)
    readonly_fields = ('created', 'updated')
    fieldsets = (
        ('Otros', {
            'fields': ('language', 'from_page'),
            'classes': ('collapse',)
        }),
        (None, {
            'fields': (
                'name',
                'last_name',
                'email',
                'subject',
                'message',
                'state'
            )
        }),
        ('Fechas', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ModalBannerModel)
class ModalBannerModelAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'is_active',
        'created', 'updated'
    )
    search_fields = ('title', 'description')
    list_filter = ('is_active',)
    ordering = ('-created',)
    readonly_fields = ('created', 'updated')
    fieldsets = (
        ('ES', {
            'fields': (
                'title',
                'description',
                'link',
                'image_file'
            )
        }),
        ('EN', {
            'fields': (
                'title_en',
                'link_en',
                'image_file_en'
            )
        }),
        ('Important', {
            'fields': ('created', 'updated', 'is_active'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeamMemberModel)
class TeamMemberModelAdmin(admin.ModelAdmin):
    list_display = (
        'display_order',
        'full_name',
        'role',
        'linkedin_admin_link',
        'is_active',
        'created',
        'photo_preview',
    )
    list_display_links = ('full_name',)
    list_editable = ('display_order', 'is_active')  # orden estable desde admin
    search_fields = ('full_name', 'role', 'linkedin_url', 'professional_summary', 'bio')
    list_filter = ('is_active',)
    ordering = ('display_order', 'full_name')
    readonly_fields = ('unique_id', 'created', 'updated', 'photo_preview')

    # Si prefieres editar slug manual, quítalo
    prepopulated_fields = {"slug": ("full_name",)}

    fieldsets = (
        ('Identidad', {
            'fields': ('unique_id', 'full_name', 'role', 'slug', 'display_order', 'is_active')
        }),
        ('LinkedIn', {
            'fields': ('linkedin_url',)
        }),
        ('Contenido', {
            'fields': ('professional_summary', 'bio')
        }),
        ('Foto', {
            'fields': ('photo', 'photo_preview')
        }),
        ('Fechas', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='LinkedIn')
    def linkedin_admin_link(self, obj):
        if not obj.linkedin_url:
            return '-'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">Abrir</a>',
            obj.linkedin_url
        )

    @admin.display(description='Foto')
    def photo_preview(self, obj):
        if not obj.photo:
            return '-'
        return format_html(
            '<img src="{}" style="height:55px;width:55px;object-fit:cover;border-radius:8px;" />',
            obj.photo.url
        )

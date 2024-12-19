from django.contrib import admin

from .models import ContactModel, ModalBannerModel


@admin.register(ContactModel)
class ContactModelAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'last_name', 'email',
        'subject', 'message', 'created',
        'state'
    )
    search_fields = ('name', 'last_name', 'email', 'subject', 'message')
    list_filter = ('is_active', 'state')
    ordering = ('-created',)
    readonly_fields = ('created', 'updated')
    fieldsets = (
        (None, {
            'fields': ('name', 'last_name', 'email', 'subject', 'message', 'state')
        }),
        ('Important dates', {
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
                'title_en', 'link_en', 'image_file_en'
            )
        }),
        ('Important', {
            'fields': ('created', 'updated', 'is_active'),
            'classes': ('collapse',)
        }),
    )

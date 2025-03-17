from django.contrib import admin

from .models import MainFAQModel, OtherFAQModel


@admin.register(MainFAQModel)
class MainFAQModelAdmin(admin.ModelAdmin):
    list_display = (
        'default_order', 'question', 'created', 'updated', 'id'
    )

    list_display_links = list_display

    search_fields = ('question', 'answer')

    ordering = ('default_order', '-created')

    readonly_fields = ('created', 'updated', 'id')

    fieldsets = (
        ('#', {
            'fields': ('default_order',)
        }),
        ('Questions', {
            'fields': ('language', 'question', 'answer')
        }),
        ('Others', {
            'fields': ('created', 'updated', 'id'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OtherFAQModel)
class OtherFAQModelAdmin(admin.ModelAdmin):
    list_display = (
        'default_order', 'question', 'created', 'updated', 'id'
    )

    list_display_links = list_display

    search_fields = ('question', 'answer', 'short_answer')

    ordering = ('default_order', '-created')

    readonly_fields = ('created', 'updated', 'id')

    fieldsets = (
        ('#', {
            'fields': ('default_order',)
        }),
        ('Questions', {
            'fields': ('language', 'question', 'short_answer', 'answer')
        }),
        ('Others', {
            'fields': ('created', 'updated', 'id'),
            'classes': ('collapse',)
        }),
    )
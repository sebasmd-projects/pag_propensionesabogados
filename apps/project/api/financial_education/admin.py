from django.contrib import admin

from .models import FinancialEducationModel


@admin.register(FinancialEducationModel)
class FinancialEducationModelAdmin(admin.ModelAdmin):
    list_display = (
        'default_order', 'id', 'video_url', 'created'
    )

    list_display_links = list_display

    search_fields = (
        'title', 'title_en', 'video_url', 'category',
        'category_en', 'description', 'description_en'
    )

    list_filter = ('is_active',)

    ordering = ('-created',)

    readonly_fields = ('created', 'updated', 'id')

    fieldsets = (
        ('#', {
            'fields': ('default_order',)
        }),
        ('ES', {
            'fields': (
                'title',
                'video_url',
                'category',
                'description'
            )
        }),
        ('EN', {
            'fields': (
                'title_en',
                'category_en',
                'description_en'
            )
        }),
        ('Otros', {
            'fields': ('is_active', 'created', 'updated', 'id'),
            'classes': ('collapse',)
        }),
    )

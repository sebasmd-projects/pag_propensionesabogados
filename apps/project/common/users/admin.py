from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django_countries import countries
from import_export.admin import ImportExportActionModelAdmin

from .models import UserModel


class UserAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.get('country_code').initial = 'CO'

        password = self.fields.get("password")
        if password:
            password.help_text = password.help_text.format(
                f"../../{self.instance.pk}/password/"
            )

    country_code = forms.ChoiceField(
        choices=[(code, f'{name} ({code})') for code, name in countries],
        widget=forms.Select(),
        required=False,
    )

    password = ReadOnlyPasswordHashField(
        label=_("password"),
        help_text=_(
            "Raw passwords are not stored, so there is no way to see this "
            "user’s password, but you can change the password using "
            '<a href="{}">this form</a>.'
        ),
    )

    class Meta:
        model = UserModel
        fields = '__all__'


@admin.register(UserModel)
class UserModelAdmin(UserAdmin, ImportExportActionModelAdmin):
    form = UserAdminForm

    search_fields = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
    )

    list_display = (
        'get_full_name',
        'username',
        'email',
        'is_staff',
        'is_active',
        'is_superuser',
        'get_groups',
    )
    
    list_filter = ("is_staff", "is_superuser", "is_active")

    list_display_links = (
        'get_full_name',
        'username',
        'email',
    )

    ordering = (
        'default_order',
        'created',
        'last_name',
        'first_name',
        'email',
        'username',
    )

    readonly_fields = [
        'created',
        'updated',
        'last_login'
    ]

    fieldsets = (
        (
            _('User Information'), {
                'fields': (
                    'username',
                    'password',
                )
            }
        ),
        (
            _('Personal Information'), {
                'fields': (
                    'first_name',
                    'last_name',
                    'email',
                    'country_code'
                )
            }
        ),
        (
            _('Permissions'), {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions'
                )
            }
        ),
        (
            _('Dates'), {
                'fields': (
                    'last_login',
                    'created',
                    'updated'
                )
            }
        ),
        (
            _('Priority'), {
                'fields': (
                    'default_order',
                )
            }
        )
    )

    def user_has_edit_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name=settings.EDIT_USERS_GROUP).exists()

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        if self.user_has_edit_permission(request):
            return True
        return obj == request.user

    def has_delete_permission(self, request, obj=None):
        if self.user_has_edit_permission(request):
            return True
        return obj == request.user

    def has_add_permission(self, request):
        return self.user_has_edit_permission(request)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.user_has_edit_permission(request):
            return qs
        return qs.filter(pk=request.user.pk)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not self.user_has_edit_permission(request) and obj == request.user:
            return (
                (
                    _('Personal Information'), {
                        'fields': (
                            'username',
                            'first_name',
                            'last_name',
                            'country_code',
                            'password'
                        )
                    }
                ),
                (
                    _('Dates'), {
                        'fields': (
                            'last_login',
                            'created',
                            'updated'
                        )
                    }
                )
            )
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if self.user_has_edit_permission(request) or obj is None:
            return form

        if obj == request.user:
            allowed_fields = [
                'username',
                'first_name',
                'last_name',
                'country_code',
                'password'
            ]
            for field_name in list(form.base_fields):
                if field_name not in allowed_fields:
                    form.base_fields.pop(field_name)
            form.base_fields['username'].widget.attrs['readonly'] = True
        else:
            raise PermissionDenied
        return form

    def get_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])

    def get_full_name(self, obj):
        return obj.get_full_name()

    get_groups.short_description = _('Groups')

    get_full_name.short_description = _('Names')

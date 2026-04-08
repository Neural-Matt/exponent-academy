from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['staff_number']
    list_display = ['staff_number', 'first_name', 'last_name', 'department', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'department', 'is_active', 'is_staff']
    search_fields = ['staff_number', 'first_name', 'last_name', 'department']

    fieldsets = (
        (None, {'fields': ('staff_number', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'department', 'job_title')}),
        (_('Role & status'), {'fields': ('role', 'is_active', 'is_staff', 'must_reset_password')}),
        (_('Permissions'), {'fields': ('is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('staff_number', 'first_name', 'last_name', 'password1', 'password2', 'role'),
        }),
    )

    readonly_fields = ['date_joined', 'last_login']

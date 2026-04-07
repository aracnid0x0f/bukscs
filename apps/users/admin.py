from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User
# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'staff_id')
    search_fields = ('email', 'first_name', 'last_name', 'staff_id')
    list_filter = ('role',)


admin.site.site_header = "BUKSCMS Admin"
admin.site.site_title = "BUKSCMS Admin Portal"

# @admin.register(User)
# class CustomUserAdmin(UserAdmin):
#     # Add our custom fields to the admin forms
#     fieldsets = UserAdmin.fieldsets + (
#         ('Clinic Info', {'fields': ('role', 'staff_id', 'phone_number')}),
#     )
#     add_fieldsets = UserAdmin.add_fieldsets + (
#         ('Clinic Info', {'fields': ('role', 'staff_id', 'phone_number', 'email')}),
#     )
#     list_display = ['email', 'staff_id', 'role', 'is_staff']
#     list_filter = ['role', 'is_staff']
#     search_fields = ['email', 'staff_id']

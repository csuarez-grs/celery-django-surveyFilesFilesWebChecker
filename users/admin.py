# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import LDAPUser


class LDAPUserAdmin(UserAdmin):
    model = LDAPUser
    list_display = ['username', 'is_superuser', 'first_name', 'last_name',
                    'email', 'department', 'description', 'title', 'office']


admin.site.register(LDAPUser, LDAPUserAdmin)

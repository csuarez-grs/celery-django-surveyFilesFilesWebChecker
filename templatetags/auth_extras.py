import os

from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.filter(name='is_gis_group')
def is_gis_group(user):
    group = Group.objects.get(name='gis')
    return True if group in user.groups.all() else False


@register.filter(name='is_automation_admin_group')
def is_automation_admin_group(user):
    group = Group.objects.get(name='automation_admin_group')
    return True if group in user.groups.all() else False

@register.filter(name='get_file_name')
def get_file_name(file_object):
    if os.path.isfile(file_object.file.name):
        return os.path.basename(file_object.file.name)
    return None


@register.simple_tag
def get_verbose_field_name(instance, field_name):
    """
    Returns verbose_name for a field.
    """
    return instance._meta.get_field(field_name).verbose_name.title()
import os

from celery.result import AsyncResult
from django import template
from django.contrib.auth.models import Group
from django.core.cache import cache

from users.models import LDAPUser

register = template.Library()


@register.filter(name='is_gis_group')
def is_gis_group(user):
    group = Group.objects.get(name='gis')
    return True if group in user.groups.all() else False


@register.filter(name='is_automation_admin_group')
def is_automation_admin_group(user):
    group = Group.objects.get(name='automation_admin_group')
    return True if group in user.groups.all() else False


@register.filter(name='is_ppp_automation_group')
def is_ppp_automation_group(user):
    group = Group.objects.get(name='ppp-automation-group')
    return True if group in user.groups.all() else False


@register.filter(name='get_file_name')
def get_file_name(file_object):
    if file_object.name:
        return os.path.basename(file_object.name)
    return None


@register.filter(name='get_folder_name')
def get_folder_name(folder_path):
    if folder_path is not None:
        return os.path.basename(folder_path)
    return None


@register.filter(name='automation_type')
def automation_type(target_field_folder):
    if target_field_folder is not None:
        return 'PPP Automation'
    else:
        return 'JXL QC & Automation'


@register.simple_tag
def get_verbose_field_name(instance, field_name):
    """
    Returns verbose_name for a field.
    """
    return instance._meta.get_field(field_name).verbose_name.title()


@register.filter('get_ldap_user_name')
def get_ldap_user_name(user_id):
    ldap_user = LDAPUser.objects.get(username=user_id)
    if ldap_user:
        return '%s %s' % (ldap_user.first_name.title(), ldap_user.last_name.title())
    else:
        return user_id


@register.filter('get_celery_task_status')
def get_celery_task_status(object_id):
    try:
        task_id = cache.get('{}_CELERY_TASK'.format(object_id))
        task_result = AsyncResult(task_id)
        return task_result.status, task_id
    except:
        return 'Unknown'

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import SurveyFileAutomation


class SurveyFileAdmin(admin.ModelAdmin):
    list_display = ('job_no', 'site_no', 'document', 'uploaded_time', 'uploader_name', 'qc_passed',
                    'exporting_types_selected', 'automation_status', 'errors')


admin.site.register(SurveyFileAutomation, SurveyFileAdmin)

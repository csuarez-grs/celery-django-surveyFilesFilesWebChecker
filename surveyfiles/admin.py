# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import SurveyFileAutomation
import os
from .models import PageNumsParser
from users.models import LDAPUser
import fortis_jxl_automation_from_web as fortis_web_automation
from SurveyFilesWebChecker.settings import automation_folder, sub_working_folder, KILL_PROCESS_AFTER


class SurveyFileAdmin(admin.ModelAdmin):
    list_display = ('job_no', 'site_no', 'document', 'uploaded_time', 'uploader_name', 'qc_passed',
                    'exporting_types_selected', 'automation_status', 'errors')

    actions = ["restart_automation_process"]

    def restart_automation_process(self, request, queryset):
        for obj in queryset:
            print(obj)
            job_no = obj.job_no
            site_no = obj.site_no
            document_path = obj.document.name
            document_name = os.path.basename(document_path)
            uploaded_time_str = obj.uploaded_time.strftime('%Y-%m-%d %H:%M:%S')

            detail_url = None
            if obj.selected_pages:
                pages_parser = PageNumsParser(obj.selected_pages)
                selected_pages_list = pages_parser.compile_nums_list()
            else:
                selected_pages_list = None

            user = LDAPUser.objects.filter(username=obj.uploader).get()

            tracking_id = obj.tracking_id
            if obj.create_gis_data == 1:
                create_gis_data = True
            else:
                create_gis_data = False

            if obj.overwriting == 1:
                overwriting = True
            else:
                overwriting = False

            exporting_types = [item.strip() for item in obj.exporting_types_selected
                               if len(item.strip()) > 0]

            if len(exporting_types) > 0:
                create_client_report = True
            else:
                create_client_report = False

            utm_sr_name = obj.utm_sr_name
            scale_value = obj.scale_value

            uploading_info = [
                obj.job_no,
                obj.site_no,
                obj.uploader,
                obj.uploader_email,
                obj.uploaded_time.strftime('%Y-%m-%d %H:%M:%S'),
                obj.project_manager,
                obj.project_manager_email,
                utm_sr_name,
                scale_value
            ]

            uploader = obj.uploader

            worker = fortis_web_automation.FortisJXLWebAutomationWorker(job_no=job_no, site_no=site_no,
                                                                        uploaded_file=document_path, uploader=uploader,
                                                                        tracking_id=tracking_id,
                                                                        create_gis_data=create_gis_data,
                                                                        site_db_path=obj.site_data_db,
                                                                        scale_factor_value=scale_value,
                                                                        utm_sr_name=utm_sr_name,
                                                                        create_reports=create_client_report,
                                                                        exporting_types=exporting_types,
                                                                        background_imagery=obj.background_imagery,
                                                                        skip_empty_pages=obj.skip_empty_pages,
                                                                        include_overview=obj.include_overview_page,
                                                                        selected_pages=obj.selected_pages,
                                                                        overwriting=obj.overwriting,
                                                                        uploading_info=uploading_info,
                                                                        kill_process_after=KILL_PROCESS_AFTER,
                                                                        web_detail_url=detail_url)

            worker.automatic_processing()


admin.site.register(SurveyFileAutomation, SurveyFileAdmin)

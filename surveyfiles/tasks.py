import sys

automation_folder = r'\\grs.com\DFS\GIS\GIS_Main\06_Tools\04_ToolBoxes\PythonToolBox\FortisProjectAutomation'
if automation_folder not in sys.path:
    sys.path.append(automation_folder)

import fortis_jxl_automation_from_web as fortis_web_automation

try:
    import ppp_automation
except:
    pass
import grs_base_classes as gbc

# from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives

from SurveyFilesWebChecker import celery_app

# from django.contrib.auth import get_user_model
#
# User = get_user_model()

from users.models import LDAPUser as User
from SurveyFilesWebChecker.settings import logger_request


# @background(schedule=0)
# def notify_user(user_id, job_no, uploaded_file, uploaded_time_str):
#     try:
#         print('Sending email')
#         # lookup user by id and send them a message
#         user = User.objects.get(pk=user_id)
#         msg_subject = '{}: JXL Files Uploading Web Notice'.format(job_no)
#         msg_content = 'Uploader: {}<br>File: {}<br>Time: {}'\
#             .format(user, uploaded_file, uploaded_time_str)
#         user.email_user(msg_subject, msg_content)
#     except Exception as e:
#         print('Errors: {}'.format(str(e)))


@celery_app.task()
def notify_uploading(username, job_no, uploaded_file, uploaded_time_str, target_field_folder):
    try:
        # lookup user by id and send them a message
        gis_email = 'gis@globalraymac.ca'
        user = User.objects.get(username=username)
        user_email = user.email
        user_name = user.username
        logger_request.info('Sending uploading confirmation email to {}'.format(user_name, uploaded_file))
        msg_subject = '{}: JXL Files Uploading Web Notice'.format(job_no)
        if target_field_folder is not None:
            msg_subject += ' (PPP Automation)'
            msg_content = '<p>Uploader: {}<br>File: {}<br>Target Field Folder: {}<br>Time: {}</p><br>' \
                .format(user_name, uploaded_file, target_field_folder, uploaded_time_str)
        else:
            msg_subject += ' (Validation)'
            msg_content = '<p>Uploader: {}<br>File: {}<br>Time: {}</p><br>' \
                .format(user_name, uploaded_file, uploaded_time_str)

        html_content = msg_content

        msg = EmailMultiAlternatives(msg_subject, msg_content, gis_email, [user_email, gis_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except Exception as e:
        logger_request.exception('Errors: {}'.format(str(e)))


@celery_app.task()
def quality_check_jxl(uploaded_file, tracking_id, create_gis_data, create_client_report,
                      exporting_types, exporting_profiles, overwriting,
                      notify_surveyor, notify_pm, uploading_info):
    logger_request.info('QC Check {}'.format(uploaded_file))
    worker = fortis_web_automation.FortisJXLWebAutomationWorker(uploaded_file=uploaded_file, tracking_id=tracking_id,
                                                                logger_name='QC',
                                                                notify_surveyor=notify_surveyor, notify_pm=notify_pm,
                                                                uploading_info=uploading_info)

    worker.qc_check()

    if worker.qc_results == 'Succeeded' and (create_gis_data or create_client_report):
        run_automation_jxl(uploaded_file, tracking_id, create_gis_data, create_client_report, exporting_types,
                           exporting_profiles,
                           overwriting, notify_pm, uploading_info=uploading_info)


@celery_app.task()
def ppp_automation_task(job_no, site_no, uploaded_file, uploading_info, scale_value, utm_sr_name, project_manager_name,
                        project_manager_email, surveyor_name, surveyor_email,
                        target_field_folder, tracking_id, overwriting, uploader_name, uploader_email):
    # type: (str, int, str, list, float, str, str, str, str, str, str, str, bool, str, str) -> None
    grs_job = gbc.GRSJob(job_no=job_no)

    jxl_file = gbc.JXLFile(jxl_path=uploaded_file, scale_value=scale_value, utm_name=utm_sr_name)

    pm = gbc.ProjectManager(employee_name=project_manager_name,
                            employee_email=project_manager_email)

    executor = gbc.GRSEmployee(employee_name=uploader_name,
                              employee_email=uploader_email)

    if surveyor_name is not None:
        surveyor = gbc.Surveyor(employee_name=surveyor_name,
                                employee_email=surveyor_email)
    else:
        surveyor = None

    field_folder = gbc.FieldFolder(
        folder_path=target_field_folder,
        job_no=job_no,
        pm=pm,
        surveyor=surveyor)

    ppp_automation_worker = ppp_automation.PPPAutomationWorker(grs_job=grs_job, site_no=site_no,
                                                               ppp_jxl=jxl_file, field_folder=field_folder,
                                                               uploading_info=uploading_info,
                                                               uploader=executor,
                                                               web_track_id=tracking_id,
                                                               overwriting=overwriting,
                                                               testing=True
                                                               )

    ppp_automation_worker.run()


def run_automation_jxl(uploaded_file, tracking_id, create_gis_data, create_client_report,
                       exporting_types, exporting_profiles, overwriting,
                       notify_pm, uploading_info):
    logger_request.info('Running automation for {}'.format(uploaded_file))

    worker = fortis_web_automation.FortisJXLWebAutomationWorker(uploaded_file=uploaded_file,
                                                                tracking_id=tracking_id,
                                                                create_gis_data=create_gis_data,
                                                                create_reports=create_client_report,
                                                                exporting_profiles=exporting_profiles,
                                                                exporting_types=exporting_types,
                                                                overwriting=overwriting,
                                                                notify_pm=notify_pm,
                                                                uploading_info=uploading_info)

    worker.automatic_processing()

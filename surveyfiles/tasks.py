import sys

automation_folder = r'\\grs.com\DFS\GIS\GIS_Main\06_Tools\04_ToolBoxes\PythonToolBox\FortisProjectAutomation'
if automation_folder not in sys.path:
    sys.path.append(automation_folder)

from fortis_jxl_automation_from_web import FortisJXLWebAutomationWorker
from fortis_automation_from_ftp_20191028 import FortisFTPTransferFolderWorker

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
def notify_uploading(username, job_no, uploaded_file, uploaded_time_str):
    try:
        # lookup user by id and send them a message
        from_email = 'gis@globalraymac.ca'
        user = User.objects.get(username=username)
        user_email = user.email
        user_name = user.username
        logger_request.info('Sending uploading confirmation email to {}'.format(user_name, uploaded_file))
        msg_subject = '{}: JXL Files Uploading Web Notice'.format(job_no)
        msg_content = '<p>Uploader: {}<br>File: {}<br>Time: {}</p><br>' \
            .format(user_name, uploaded_file, uploaded_time_str)

        html_content = msg_content

        msg = EmailMultiAlternatives(msg_subject, msg_content, from_email, [user_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except Exception as e:
        logger_request.exception('Errors: {}'.format(str(e)))


@celery_app.task()
def quality_check_jxl(uploaded_file, tracking_id, create_gis_data, create_client_report,
                      exporting_types, exporting_profiles, overwriting,
                      notify_surveyor, notify_pm, uploading_info):
    logger_request.info('QC Check {}'.format(uploaded_file))
    worker = FortisJXLWebAutomationWorker(uploaded_file=uploaded_file, tracking_id=tracking_id, logger_name='QC',
                                          notify_surveyor=notify_surveyor, notify_pm=notify_pm,
                                          uploading_info=uploading_info)

    worker.qc_check()

    if worker.qc_results == 'Succeeded' and (create_gis_data or create_client_report):
        run_automation_jxl(uploaded_file, tracking_id, create_gis_data, create_client_report, exporting_types,
                           exporting_profiles,
                           overwriting, notify_pm, uploading_info=uploading_info)


@celery_app.task()
def ppp_automation(uploaded_file, tracking_id, overwriting, target_field_folder, utm_sr_name, scale_value,
                   uploading_info, job_no, site_no):
    logger_request.info('QC Check {}'.format(uploaded_file))
    logger_request.info('Target field folder: {}'.format(target_field_folder))
    logger_request.info('Uploading Info: {}'.format(uploading_info))
    logger_request.info('Job Number: {}'.format(job_no))
    worker = FortisJXLWebAutomationWorker(uploaded_file=uploaded_file, tracking_id=tracking_id,
                                          logger_name='QC',
                                          uploading_info=uploading_info)

    worker.qc_check()

    if worker.qc_results == 'Succeeded':
        ppp_automation_tuple = (uploaded_file, target_field_folder, utm_sr_name, scale_value, site_no)
        run_automation_jxl(uploaded_file, tracking_id, create_gis_data=True,
                           create_client_report=True, exporting_types=None,
                           exporting_profiles=None,
                           overwriting=overwriting, notify_pm=False, uploading_info=uploading_info,
                           ppp_automation_tuple=ppp_automation_tuple, job_no=job_no)


def run_automation_jxl(uploaded_file, tracking_id, create_gis_data, create_client_report,
                       exporting_types, exporting_profiles, overwriting,
                       notify_pm, uploading_info, ppp_automation_tuple=None, job_no=None):
    logger_request.info('Running automation for {}'.format(uploaded_file))

    if ppp_automation_tuple is None:
        worker = FortisJXLWebAutomationWorker(uploaded_file=uploaded_file,
                                              tracking_id=tracking_id,
                                              create_gis_data=create_gis_data,
                                              create_reports=create_client_report,
                                              exporting_profiles=exporting_profiles,
                                              exporting_types=exporting_types,
                                              overwriting=overwriting,
                                              notify_pm=notify_pm,
                                              uploading_info=uploading_info)

        worker.automatic_processing()
    else:
        # TODO Implement new ppp automation here
        pass

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re
import time

from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, FormView
# Create your views here.
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from pure_pagination.mixins import PaginationMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect

from .filters import SurveyFileAutomationFilter
from .forms import SurveyFileAutomationForm, PPPFileAutomationForm, JobSetUpForm, DataExportForm
from .models import SurveyFileAutomation, fortis_job_no_pattern
from .tables import SurveyFileAutomationTable
from .tasks import *

from SurveyFilesWebChecker.settings import logger_request, task_queue
from django.core.mail import send_mail
from SurveyFilesWebChecker.settings import EMAIL_HOST_USER


class JobSetUpView(SuccessMessageMixin, FormView):
    template_name = 'surveyfiles/job_setup.html'
    form_class = JobSetUpForm
    success_message = "%(job_no)s sketch pdf setup is submitted successfully !" \
                      " Please wait for result emails"
    success_url = reverse_lazy('surveyfiles:sketch_pdf_setup_view')

    def send_email(self, job_no, log_path):
        recipient_list = ['gis@globalraymac.ca']
        if self.request.user is not None:
            recipient_list.append(self.request.user.email)

        subject = '{} job sketch pdf set up is requested'.format(job_no)
        if sub_working_folder == 'Dev':
            subject += ' ({})'.format(sub_working_folder)

        send_mail(
            subject=subject,
            message='Sketch pdf will be created for job {}.\n\nChecking log:\n{}\n\n'.format(job_no, log_path),
            from_email=EMAIL_HOST_USER,
            recipient_list=recipient_list
        )

    # def get_form_kwargs(self):
    #     kwargs = super(JobSetUpView, self).get_form_kwargs()
    #     kwargs.update({'user': self.request.user})
    #     return kwargs

    def form_valid(self, form):
        job_no = str(form.cleaned_data.get('job_no')).upper()
        background_imagery = form.cleaned_data.get('background_imagery')
        selected_sites = [item.strip() for item in str(form.cleaned_data['selected_sites']).strip().split(',')
                          if len(item.strip()) > 0]
        if selected_sites:
            selected_sites = [int(item) for item in selected_sites]
        user = self.request.user
        user_name = user.username
        # print(job_no, user_id)
        log_path = os.path.join(fortis_web_automation.log_folder, 'JobSketchSetUp_{}_{}_{}.txt' \
                                .format(job_no, user_name, time.strftime('%Y%m%d_%H%M%S')))
        self.send_email(job_no, log_path)
        args = (job_no, selected_sites, background_imagery, user_name, log_path)
        job_sketch_setup.si(*args) \
            .set(queue=task_queue) \
            .apply_async()
        return super(JobSetUpView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        print('clean data: {}'.format(cleaned_data))
        job_no = cleaned_data.get('job_no')
        print('Job no: {}'.format(job_no))

        # args = (document_path, tracking_id, raise_invalid_errors, create_gis_data, create_client_report,
        #         exporting_types,
        #         overwriting, uploading_info)
        #
        # quality_check_jxl_task = quality_check_jxl.si(*args).set(queue=task_queue)
        # quality_check_jxl_task.apply_async()

        return self.success_message % dict(
            job_no=job_no,
        )

    def get_context_data(self, **kwargs):
        context = super(JobSetUpView, self).get_context_data(**kwargs)

        extra = {'username': self.request.user.username}

        worker_status, worker_count = get_worker_status(self, extra)

        if worker_count == 0:
            self.template_name = 'surveyfiles/errors_page.html'
            context['errors'] = '<p>No any task worker is running !</p>' \
                                '<p>Please contact GIS to check the status !</p>'

        if worker_status is not None:
            context['worker_status'] = worker_status

        return context

    def get_form_kwargs(self):
        kwargs = super(JobSetUpView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs


class SurveyFilesListFilterView(SingleTableMixin, FilterView, PaginationMixin, ListView):
    model = SurveyFileAutomation
    template_name = 'surveyfiles/jxl_list.html'
    table_class = SurveyFileAutomationTable
    filterset_class = SurveyFileAutomationFilter

    paginate_by = 10


class SurveyFilesCardsFilterView(FilterView, PaginationMixin, ListView):
    model = SurveyFileAutomation
    template_name = 'surveyfiles/jxl_cards.html'
    filterset_class = SurveyFileAutomationFilter

    paginate_by = 10

    # Limit records for uploaded at the specific branch
    # def get_queryset(self):
    #     valid_id_list = [object.tracking_id for object in SurveyFileAutomation.objects.all()
    #                      if os.path.isfile(object.document.path)]
    #     return SurveyFileAutomation.objects.filter(tracking_id__in=valid_id_list)

    def get_form_kwargs(self):
        kwargs = super(SurveyFilesCardsFilterView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(SurveyFilesCardsFilterView, self).get_context_data(**kwargs)

        extra = {'username': self.request.user.username}

        worker_status = get_worker_status(self, extra)[0]
        if worker_status is not None:
            context['worker_status'] = worker_status

        return context


def get_worker_status(self, extra):
    if self.request.user is not None:
        try:
            results = celery_app.control.ping()
            good_worker_count = 0
            total_worker = len(results)
            for index, worker_dict in enumerate(results):
                values = worker_dict.values()
                for response_dict in values:
                    good_action = response_dict.get('ok')
                    if str(good_action).lower() == 'pong':
                        good_worker_count += 1
            if good_worker_count == 0:
                worker_status = 'No any worker ({} assigned workers) is working !!!'.format(total_worker)
            else:
                worker_status = '{} of {} worker(s) are working.'.format(good_worker_count, total_worker)

            logger_request.info('Worker status: {}'.format(worker_status), extra=extra)
            return worker_status, good_worker_count
        except Exception as e:
            logger_request.exception('Failed to get worker status: {}'.format(e), extra=extra)
            return None, 0
    else:
        return None, 0


class CreateSurveyFileAutomationView(SuccessMessageMixin, CreateView):
    model = SurveyFileAutomation
    form_class = SurveyFileAutomationForm
    template_name = 'surveyfiles/jxl_upload.html'
    success_url = reverse_lazy('surveyfiles:jxl_create_view')
    # success_url = '/success/'
    success_message = "%(file_name)s - Site %(site_no)s - %(utm_sr_name)s - %(scale_value)s was uploaded successfully !" \
                      " Please wait for QC emails"

    def get_form_kwargs(self):
        kwargs = super(CreateSurveyFileAutomationView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def form_invalid(self, form):
        logger_request.info('form is not valid: {}'.format(self.get_context_data(form=form)),
                            extra={'username': self.request.user.username})
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        logger_request.info('validating form', extra={'username': self.request.user.username})
        logger_request.info('user: {}'.format(self.request.user.username),
                            extra={'username': self.request.user.username})
        logger_request.info('call saving in form', extra={'username': self.request.user.username})
        form.save()
        logger_request.info('saved in form successfully', extra={'username': self.request.user.username})
        logger_request.info('Document: {}'.format(self.request.FILES[u'document']),
                            extra={'username': self.request.user.username})
        return super(CreateSurveyFileAutomationView, self).form_valid(form)

        # return self.render_to_response(self.get_context_data(
        #     form=form,
        #     uploaded_file=self.request.FILES[u'document']))

    def get_success_message(self, cleaned_data):
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.request.user.username})
        logger_request.info('user id: {} type - {}'.format(self.request.user.id, type(self.request.user.id)),
                            extra={'username': self.request.user.username})
        uploader_usernane = self.request.user.username
        job_no = self.object.job_no
        site_no = self.object.site_no
        utm_sr_name = self.object.utm_sr_name
        scale_value = self.object.scale_value
        document_path = self.object.document.file.name
        document_name = os.path.basename(document_path)
        uploaded_time_str = self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S')
        target_field_folder = self.object.target_field_folder

        args = (uploader_usernane, job_no, document_name, uploaded_time_str, target_field_folder)
        notify_uploading.si(*args) \
            .set(queue=task_queue) \
            .apply_async()
        # uploader = self.object.uploader
        # uploader_email = self.object.uploader_email
        # uploaded_time = self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S')
        # project_manager = self.object.project_manager
        # project_manager_email = self.object.project_manager_email
        tracking_id = self.object.tracking_id

        # if self.object.create_data_report == 1 and os.path.basename(document_path)[-4:].lower() == '.jxl':

        # if self.object.raise_invalid_errors == 1:
        #     raise_invalid_errors = True
        # else:
        #     raise_invalid_errors = False

        if self.object.create_gis_data == 1:
            create_gis_data = True
        else:
            create_gis_data = False

        if self.object.overwriting == 1:
            overwriting = True
        else:
            overwriting = False

        exporting_types = [item.strip() for item in self.object.exporting_types_selected
                           if len(item.strip()) > 0]

        if len(exporting_types) > 0:
            create_client_report = True
        else:
            create_client_report = False

        uploading_info = [
            self.object.job_no,
            self.object.site_no,
            self.object.uploader,
            self.object.uploader_email,
            self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S'),
            self.object.project_manager,
            self.object.project_manager_email,
            self.object.utm_sr_name,
            self.object.scale_value
        ]

        uploader = self.object.uploader
        args = (job_no, site_no, document_path, uploader, tracking_id, create_gis_data, create_client_report,
                exporting_types,
                overwriting, uploading_info)

        quality_check_jxl_task = quality_check_jxl.si(*args).set(queue=task_queue)
        quality_check_jxl_task.apply_async()

        return self.success_message % dict(
            cleaned_data,
            file_name=os.path.basename(self.object.document.file.name),
            site_no=site_no,
            utm_sr_name=utm_sr_name,
            scale_value=scale_value,
            # uploader=self.object.uploader
        )

    def get_context_data(self, **kwargs):
        context = super(CreateSurveyFileAutomationView, self).get_context_data(**kwargs)

        extra = {'username': self.request.user.username}

        worker_status, worker_count = get_worker_status(self, extra)

        if worker_count == 0:
            self.template_name = 'surveyfiles/errors_page.html'
            context['errors'] = '<p>No any task worker is running !</p>' \
                                '<p>Please contact GIS to check the status !</p>'

        if worker_status is not None:
            context['worker_status'] = worker_status

        return context

    # def get_context_data(self, **kwargs):
    #     context = super(CreateJXLFileAutomationView, self).get_context_data(**kwargs)
    #     try:
    #         context['uploaded_file'] = self.request.FILES[u'document']
    #     except:
    #         pass
    #
    #     return context

    # def get_success_url(self, *args, **kwargs):
    #     return reverse('jxlfiles:jxl_list_view')


class DataExportView(SuccessMessageMixin, FormView):
    template_name = 'surveyfiles/data_export.html'
    form_class = DataExportForm
    success_message = "%(exporting_types)s will be created based on the data in %(site_db_path)s !" \
                      " Please wait for result emails - %(log_path)s"
    success_url = reverse_lazy('surveyfiles:data_export_view')

    def __init__(self, *args, **kwargs):
        super(DataExportView, self).__init__(*args, **kwargs)
        self.log_path = None

    def get_form_kwargs(self):
        kwargs = super(DataExportView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def send_email(self, job_no, site_db_path, site_no, exporting_types, log_path):
        recipient_list = ['gis@globalraymac.ca']
        if self.request.user is not None:
            recipient_list.append(self.request.user.email)

        subject = '{} job data exporting is requested'.format(job_no)
        if sub_working_folder == 'Dev':
            subject += ' ({})'.format(sub_working_folder)

        send_mail(
            subject=subject,
            message='{} will be created based on data in geodatabase as below for job {} site {}.'
                    '\n{}\n\nChecking log:\n{}\n\n'.format(','.join(exporting_types),
                                                           job_no, site_no,
                                                           ma.hyperLinkFileFullName(site_db_path),
                                                           log_path),
            from_email=EMAIL_HOST_USER,
            recipient_list=recipient_list
        )

    def form_valid(self, form):
        site_db_path = form.cleaned_data.get('site_db_path')
        site_no = form.cleaned_data.get('site_no')
        source_jxl_path = form.cleaned_data.get('source_jxl_path')
        exporting_types_selected = form.cleaned_data.get('exporting_types_selected')
        exporting_types = [item.strip() for item in exporting_types_selected
                           if len(item.strip()) > 0]
        background_imagery = form.cleaned_data.get('background_imagery')
        overwriting = form.cleaned_data.get('overwriting')
        # overwriting = False
        job_no = re.search(fortis_job_no_pattern, os.path.basename(site_db_path)).groups()[0]

        site_no_pattern = re.compile('Site_(\d+)\.gdb', re.IGNORECASE)
        if site_no is None:
            site_no = int(re.search(site_no_pattern, os.path.basename(site_db_path)).groups()[0])

        user = self.request.user
        user_name = user.username
        self.log_path = os.path.join(fortis_web_automation.log_folder, 'DataExporting_{}_{}_{}.txt' \
                                     .format(job_no, user_name, time.strftime('%Y%m%d_%H%M%S')))
        # print(job_no, user_id)

        self.send_email(job_no, site_db_path, site_no, exporting_types, self.log_path)
        args = (job_no, site_no, site_db_path, source_jxl_path, exporting_types, background_imagery
                , user_name, self.log_path, overwriting)
        data_export.si(*args) \
            .set(queue=task_queue) \
            .apply_async()
        return super(DataExportView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        print('clean data: {}'.format(cleaned_data))
        site_db_path = cleaned_data.get('site_db_path')
        exporting_types_selected = cleaned_data.get('exporting_types_selected')
        exporting_types = [item.strip() for item in exporting_types_selected
                           if len(item.strip()) > 0]
        print('Site db path: {}'.format(site_db_path))

        return self.success_message % dict(
            cleaned_data,
            site_db_path=os.path.basename(site_db_path),
            exporting_types=','.join(exporting_types),
            log_path=ma.hyperLinkFileBasename(self.log_path)
        )

    def get_context_data(self, **kwargs):
        context = super(DataExportView, self).get_context_data(**kwargs)

        extra = {'username': self.request.user.username}

        worker_status, worker_count = get_worker_status(self, extra)

        if worker_count == 0:
            self.template_name = 'surveyfiles/errors_page.html'
            context['errors'] = '<p>No any task worker is running !</p>' \
                                '<p>Please contact GIS to check the status !</p>'

        if worker_status is not None:
            context['worker_status'] = worker_status

        return context


class CreatePPPFileAutomationView(SuccessMessageMixin, CreateView):
    model = SurveyFileAutomation
    form_class = PPPFileAutomationForm
    template_name = 'surveyfiles/ppp_automation.html'
    success_url = reverse_lazy('surveyfiles:ppp_automation_view')
    # success_url = '/success/'
    success_message = "%(file_name)s - Site %(site_no)s - %(utm_sr_name)s - %(scale_value)s was uploaded successfully !" \
                      " Please wait for QC emails"

    def get_form_kwargs(self):
        kwargs = super(CreatePPPFileAutomationView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def form_invalid(self, form):
        logger_request.info('form is not valid: {}'.format(self.get_context_data(form=form)),
                            extra={'username': self.request.user.username})
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        logger_request.info('validating form', extra={'username': self.request.user.username})
        logger_request.info('user: {}'.format(self.request.user.username),
                            extra={'username': self.request.user.username})
        logger_request.info('call saving in form', extra={'username': self.request.user.username})
        form.save()
        logger_request.info('saved in form successfully', extra={'username': self.request.user.username})
        logger_request.info('Document: {}'.format(self.request.FILES[u'document']),
                            extra={'username': self.request.user.username})
        return super(CreatePPPFileAutomationView, self).form_valid(form)

        # return self.render_to_response(self.get_context_data(
        #     form=form,
        #     uploaded_file=self.request.FILES[u'document']))

    def get_success_message(self, cleaned_data):
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.request.user.username})
        logger_request.info('user id: {} type - {}'.format(self.request.user.id, type(self.request.user.id)),
                            extra={'username': self.request.user.username})
        uploader_usernane = self.request.user.username
        job_no = self.object.job_no
        site_no = self.object.site_no
        utm_sr_name = self.object.utm_sr_name
        scale_value = self.object.scale_value
        uploaded_file = self.object.document.file.name
        document_name = os.path.basename(uploaded_file)
        uploaded_time_str = self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S')
        project_manager_name = self.object.project_manager
        project_manager_email = self.object.project_manager_email
        surveyor_name = self.object.surveyor_name
        surveyor_email = self.object.surveyor_email
        target_field_folder = self.object.target_field_folder

        args = (uploader_usernane, job_no, document_name, uploaded_time_str, target_field_folder)
        notify_uploading.si(*args) \
            .set(queue=task_queue) \
            .apply_async()
        tracking_id = self.object.tracking_id
        target_field_folder = self.object.target_field_folder

        if self.object.overwriting == 1:
            overwriting = True
        else:
            overwriting = False

        uploading_info = [
            self.object.job_no,
            self.object.site_no,
            self.object.uploader,
            self.object.uploader_email,
            self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S'),
            self.object.project_manager,
            self.object.project_manager_email,
            self.object.utm_sr_name,
            self.object.scale_value,
        ]

        args = (job_no, site_no, uploaded_file, uploading_info, scale_value, utm_sr_name, project_manager_name,
                project_manager_email, surveyor_name, surveyor_email,
                target_field_folder, tracking_id, overwriting, self.object.uploader_name, self.object.uploader_email)

        ppp_automation_task_func = ppp_automation_task.si(*args).set(queue=task_queue)
        ppp_automation_task_func.apply_async()

        return self.success_message % dict(
            cleaned_data,
            file_name=os.path.basename(self.object.document.file.name),
            site_no=site_no,
            utm_sr_name=utm_sr_name,
            scale_value=scale_value,
            # uploader=self.object.uploader
        )

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='ppp-automation-group').exists():
            return super(CreatePPPFileAutomationView, self).dispatch(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_context_data(self, **kwargs):
        context = super(CreatePPPFileAutomationView, self).get_context_data(**kwargs)

        extra = {'username': self.request.user.username}

        worker_status, worker_count = get_worker_status(self, extra)

        if worker_count == 0:
            self.template_name = 'surveyfiles/errors_page.html'
            context['errors'] = '<p>No any task worker is running !</p>' \
                                '<p>Please contact GIS to check the status !</p>'

        if worker_status is not None:
            context['worker_status'] = worker_status

        return context

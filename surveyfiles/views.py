# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
# Create your views here.
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from pure_pagination.mixins import PaginationMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect

from .filters import SurveyFileAutomationFilter
from .forms import SurveyFileAutomationForm, PPPFileAutomationForm
from .models import SurveyFileAutomation
from .tables import SurveyFileAutomationTable
from .tasks import *

from SurveyFilesWebChecker.settings import logger_request, task_queue


class SurveyFilesListFilterView(SingleTableMixin, FilterView, PaginationMixin, ListView):
    model = SurveyFileAutomation
    template_name = 'surveyfiles/jxl_list.html'
    table_class = SurveyFileAutomationTable
    filterset_class = SurveyFileAutomationFilter

    paginate_by = 10

    def get_queryset(self):
        valid_id_list = [object.tracking_id for object in SurveyFileAutomation.objects.all()
                         if os.path.isfile(object.document.path)]
        return SurveyFileAutomation.objects.filter(tracking_id__in=valid_id_list)


class SurveyFilesCardsFilterView(FilterView, PaginationMixin, ListView):
    model = SurveyFileAutomation
    template_name = 'surveyfiles/jxl_cards.html'
    filterset_class = SurveyFileAutomationFilter

    paginate_by = 10

    def get_queryset(self):
        valid_id_list = [object.tracking_id for object in SurveyFileAutomation.objects.all()
                         if os.path.isfile(object.document.path)]
        return SurveyFileAutomation.objects.filter(tracking_id__in=valid_id_list)

    def get_form_kwargs(self):
        kwargs = super(SurveyFilesCardsFilterView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(SurveyFilesCardsFilterView, self).get_context_data(**kwargs)

        extra = {'username': self.request.user.username}
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

                context['worker_status'] = worker_status

                logger_request.info('Worker status: {}'.format(context['worker_status']), extra=extra)
            except Exception as e:
                logger_request.exception('Failed to get worker status: {}'.format(e), extra=extra)

        return context


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

        if self.object.raise_invalid_errors == 1:
            raise_invalid_errors = True
        else:
            raise_invalid_errors = False

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

        args = (document_path, tracking_id, raise_invalid_errors, create_gis_data, create_client_report,
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


class DataExportView(SuccessMessageMixin, CreateView):
    model = SurveyFileAutomation
    form_class = SurveyFileAutomationForm
    template_name = 'surveyfiles/jxl_upload.html'
    success_url = reverse_lazy('surveyfiles:jxl_create_view')
    # success_url = '/success/'
    success_message = "%(file_name)s - Site %(site_no)s - %(utm_sr_name)s - %(scale_value)s was uploaded successfully !" \
                      " Please wait for QC emails"

    def get_form_kwargs(self):
        kwargs = super(DataExportView, self).get_form_kwargs()
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
        return super(DataExportView, self).form_valid(form)

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

        if self.object.raise_invalid_errors == 1:
            raise_invalid_errors = True
        else:
            raise_invalid_errors = False

        if self.object.site_data_db is None:
            site_data_db = None
            if self.object.create_gis_data == 1:
                create_gis_data = True
            else:
                create_gis_data = False
        else:
            create_gis_data = False
            site_data_db = self.object.site_data_db

        if self.object.create_client_report == 1:
            create_client_report = True
        else:
            create_client_report = False

        if self.object.overwriting == 1:
            overwriting = True
        else:
            overwriting = False

        if self.object.notify_surveyor == 1:
            notify_surveyor = True
        else:
            notify_surveyor = False

        if self.object.notify_pm == 1:
            notify_pm = True
        else:
            notify_pm = False

        exporting_types = [item.strip() for item in self.object.exporting_types_selected
                           if len(item.strip()) > 0]

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

        args = (document_path, tracking_id, raise_invalid_errors, site_data_db, create_gis_data, create_client_report,
                exporting_types,
                overwriting, notify_surveyor, notify_pm, uploading_info)

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

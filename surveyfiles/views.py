# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import time

from django.core.exceptions import ValidationError
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, FormView, DetailView
# Create your views here.
from django.views.generic.edit import FormMixin
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from pure_pagination.mixins import PaginationMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.core.cache import cache

from .filters import SurveyFileAutomationFilter
from .forms import SurveyFileAutomationForm, PPPFileAutomationForm, JobSetUpForm, DataExportForm
from .models import SurveyFileAutomation, FORTIS_JOB_NO_PATTERN, FortisJobExtents, PageNumsParser
from .tables import SurveyFileAutomationTable
from .tasks import *

from SurveyFilesWebChecker.settings import logger_request, task_queue
from django.core.mail import send_mail
from SurveyFilesWebChecker.settings import EMAIL_HOST_USER, dev_test, ALLOW_WORKER_OFFLINE


class JobSetUpView(SuccessMessageMixin, FormView):
    template_name = 'surveyfiles/job_setup.html'
    form_class = JobSetUpForm
    success_message = "%(job_no)s sketch pdf setup is submitted successfully !" \
                      " Please wait for result emails - %(log_path)s"
    success_url = reverse_lazy('surveyfiles:sketch_pdf_setup_view')

    def __init__(self, *args, **kwargs):
        super(JobSetUpView, self).__init__(*args, **kwargs)
        self.log_path = None

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
        self.log_path = os.path.join(fortis_web_automation.WEB_LOG_FOLDER, 'JobSketchSetUp_{}_{}_{}.txt' \
                                     .format(job_no, user_name, time.strftime('%Y%m%d_%H%M%S')))
        self.send_email(job_no, self.log_path)
        args = (job_no, selected_sites, background_imagery, user_name, self.log_path)
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
            log_path=ma.hyperLinkFileBasename(self.log_path)
        )

    def get_context_data(self, **kwargs):
        context = super(JobSetUpView, self).get_context_data(**kwargs)

        extra = {'username': self.request.user.username}

        worker_status, worker_count = get_worker_status(self, extra)

        if worker_count == 0 and not ALLOW_WORKER_OFFLINE:
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

    def get_queryset(self):
        return SurveyFileAutomation.objects.filter(dev_test=dev_test)


class SurveyFileDetailView(DetailView):
    model = SurveyFileAutomation
    template_name = 'surveyfiles/details_page.html'


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

    def get_queryset(self):
        return SurveyFileAutomation.objects.filter(dev_test=dev_test)

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

    def __init__(self, **kwargs):
        super(CreateSurveyFileAutomationView, self).__init__(**kwargs)
        self.reference_object = None
        self.site_data_db = None

    def get_success_url(self):
        return reverse('surveyfiles:details_view', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super(CreateSurveyFileAutomationView, self).get_initial()
        reference_id = self.request.GET.get('reference_id')
        if reference_id:
            self.reference_object = SurveyFileAutomation.objects.get(tracking_id=reference_id)
            self.site_data_db = self.reference_object.site_data_db
        else:
            self.reference_object = None
        if self.reference_object:
            initial.update({
                'document': self.reference_object.document,
                'extract_input_values': False,
                'utm_sr_name': self.reference_object.utm_sr_name,
                'scale_value': self.reference_object.scale_value,
                'create_gis_data': False,
                'site_data_db': self.reference_object.site_data_db,
                'site_no': self.reference_object.site_no,
                'exporting_types_selected': self.reference_object.exporting_types_selected,
                'background_imagery': self.reference_object.background_imagery,
                'selected_pages': self.reference_object.selected_pages,
                # 'skip_empty_pages': self.reference_object.skip_empty_pages,
                'skip_empty_pages': False,
                'include_overview_page': self.reference_object.include_overview_page,
            })
        return initial

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
        # logger_request.info('Document: {}'.format(self.request.FILES[u'document']),
        #                     extra={'username': self.request.user.username})
        response = super(CreateSurveyFileAutomationView, self).form_valid(form)
        self.run_tasks(form.cleaned_data)
        return response

    def run_tasks(self, cleaned_data):
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.request.user.username})
        logger_request.info('user id: {} type - {}'.format(self.request.user.id, type(self.request.user.id)),
                            extra={'username': self.request.user.username})
        job_no = self.object.job_no
        site_no = self.object.site_no
        document_path = self.object.document.file.name
        document_name = os.path.basename(document_path)

        uploaded_time_str = self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S')

        detail_url = self.request.build_absolute_uri(
            reverse('surveyfiles:details_view', kwargs={'pk': self.object.tracking_id}))

        if self.object.selected_pages:
            pages_parser = PageNumsParser(self.object.selected_pages)
            selected_pages_list = pages_parser.compile_nums_list()
        else:
            selected_pages_list = None

        kwargs = dict(username=self.request.user.username,
                      job_no=job_no,
                      uploaded_file=document_name,
                      site_data_db=self.site_data_db,
                      uploaded_time_str=uploaded_time_str,
                      target_field_folder=self.object.target_field_folder,
                      utm_sr_name=self.object.utm_sr_name,
                      scale_factor=self.object.scale_value,
                      exporting_types=self.object.exporting_types_selected,
                      background_imagery=self.object.background_imagery,
                      skip_empty_pages=self.object.skip_empty_pages,
                      include_overview_page=self.object.include_overview_page,
                      selected_pages=selected_pages_list,
                      detail_url=detail_url,
                      )
        notify_uploading.si(**kwargs) \
            .set(queue=task_queue) \
            .apply_async()

        tracking_id = self.object.tracking_id

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

        utm_sr_name = self.object.utm_sr_name
        scale_value = self.object.scale_value

        uploading_info = [
            self.object.job_no,
            self.object.site_no,
            self.object.uploader,
            self.object.uploader_email,
            self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S'),
            self.object.project_manager,
            self.object.project_manager_email,
            utm_sr_name,
            scale_value
        ]

        uploader = self.object.uploader
        kwargs = dict(job_no=job_no,
                      site_no=site_no,
                      uploaded_file=document_path,
                      uploader=uploader,
                      tracking_id=tracking_id,
                      create_gis_data=create_gis_data,
                      site_data_db=self.site_data_db,
                      utm_sr_name=utm_sr_name,
                      scale_value=scale_value,
                      create_client_report=create_client_report,
                      exporting_types=exporting_types,
                      background_imagery=self.object.background_imagery,
                      overwriting=overwriting,
                      uploading_info=uploading_info,
                      skip_empty_pages=self.object.skip_empty_pages,
                      include_overview_page=self.object.include_overview_page,
                      selected_pages=selected_pages_list,
                      detail_url=detail_url,
                      )

        quality_check_jxl_task = quality_check_jxl.si(**kwargs).set(queue=task_queue)
        celery_task = quality_check_jxl_task.apply_async()
        cache.set('{}_CELERY_TASK'.format(self.object.tracking_id), celery_task.id)

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

        if worker_count == 0 and not ALLOW_WORKER_OFFLINE:
            self.template_name = 'surveyfiles/errors_page.html'
            context['errors'] = '<p>No any task worker is running !</p>' \
                                '<p>Please contact GIS to check the status !</p>'

        if worker_status is not None:
            context['worker_status'] = worker_status

        if self.reference_object:
            context['reference_object'] = self.reference_object

        return context


class DataExportView(SuccessMessageMixin, FormView):
    template_name = 'surveyfiles/data_export.html'
    form_class = DataExportForm
    success_message = "%(exporting_types)s will be created based on the data in %(site_db_path)s !" \
                      " Please wait for result emails - %(log_path)s"
    success_url = reverse_lazy('surveyfiles:data_export_view')

    def __init__(self, *args, **kwargs):
        super(DataExportView, self).__init__(*args, **kwargs)
        self.log_path = None

    def get_initial(self):
        initial = super(DataExportView, self).get_initial()
        reference_id = self.request.GET.get('reference_id')
        if reference_id:
            automation_object = SurveyFileAutomation.objects.get(tracking_id=reference_id)
            if automation_object:
                initial.update({
                    'site_db_path': automation_object.site_data_db,
                    'site_no': automation_object.site_no,
                    'exporting_types_selected': automation_object.exporting_types_selected
                })
        return initial

    def get_form_kwargs(self):
        kwargs = super(DataExportView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        # print('view kwargs: {}'.format(kwargs))
        return kwargs

    def send_email(self, job_no, site_db_path, site_no, exporting_types, log_path, contact_emails):
        recipient_list = ['gis@globalraymac.ca']
        if self.request.user is not None:
            recipient_list.append(self.request.user.email)

        if contact_emails:
            recipient_list.extend(contact_emails)

        subject = '{} job data exporting is requested by {}'.format(job_no, self.request.user)
        if sub_working_folder == 'Dev':
            subject += ' ({})'.format(sub_working_folder)

        send_mail(
            subject=subject,
            message='As requested by {}, {} will be created based on data in geodatabase as below for job {} site {}.'
                    '\n{}\n\nChecking log:\n{}\n\n'.format(self.request.user,
                                                           ','.join(exporting_types),
                                                           job_no, site_no,
                                                           site_db_path,
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
        contact_emails = [str(item).strip() for item in re.split('[,;\s]+', form.cleaned_data.get('contact_emails'))
                          if len(str(item).strip()) > 0]
        # overwriting = False
        job_no = re.search(FORTIS_JOB_NO_PATTERN, os.path.basename(site_db_path)).groups()[0]

        site_no_pattern = re.compile('Site_(\d+)\.gdb', re.IGNORECASE)
        if site_no is None:
            site_no = int(re.search(site_no_pattern, os.path.basename(site_db_path)).groups()[0])

        user = self.request.user
        user_name = user.username
        self.log_path = os.path.join(fortis_web_automation.WEB_LOG_FOLDER, 'DataExporting_{}_{}_{}.txt' \
                                     .format(job_no, user_name, time.strftime('%Y%m%d_%H%M%S')))
        # print(job_no, user_id)

        self.send_email(job_no, site_db_path, site_no, exporting_types, self.log_path, contact_emails)
        args = (job_no, site_no, site_db_path, source_jxl_path, exporting_types, background_imagery
                , user_name, self.log_path, overwriting, contact_emails)
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

        if worker_count == 0 and not ALLOW_WORKER_OFFLINE:
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
        # logger_request.info('user id: {} type - {}'.format(self.request.user.id, type(self.request.user.id)),
        #                     extra={'username': self.request.user.username})
        # uploader_usernane = self.request.user.username
        job_no = self.object.job_no
        site_no = self.object.site_no
        utm_sr_name = self.object.utm_sr_name
        scale_value = self.object.scale_value
        uploaded_file = self.object.document.file.name
        site_data_db = self.object.site_data_db
        document_name = os.path.basename(uploaded_file)
        uploaded_time_str = self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S')
        project_manager_name = self.object.project_manager
        project_manager_email = self.object.project_manager_email
        surveyor_name = self.object.surveyor_name
        surveyor_email = self.object.surveyor_email
        target_field_folder = self.object.target_field_folder

        detail_url = self.request.build_absolute_uri(
            reverse('surveyfiles:details_view', kwargs={'pk': self.object.tracking_id}))

        kwargs = dict(username=self.request.user.username,
                      job_no=job_no,
                      uploaded_file=document_name,
                      uploaded_time_str=uploaded_time_str,
                      target_field_folder=self.object.target_field_folder,
                      utm_sr_name=self.object.utm_sr_name,
                      scale_factor=self.object.scale_value,
                      exporting_types=self.object.exporting_types_selected,
                      site_data_db=site_data_db,
                      detail_url=detail_url,
                      )
        notify_uploading.si(**kwargs) \
            .set(queue=task_queue) \
            .apply_async()
        tracking_id = self.object.tracking_id

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
                project_manager_email, surveyor_name, surveyor_email, site_data_db,
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

        if worker_count == 0 and not ALLOW_WORKER_OFFLINE:
            self.template_name = 'surveyfiles/errors_page.html'
            context['errors'] = '<p>No any task worker is running !</p>' \
                                '<p>Please contact GIS to check the status !</p>'

        if worker_status is not None:
            context['worker_status'] = worker_status

        return context

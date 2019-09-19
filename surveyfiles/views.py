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

from .filters import SurveyFileAutomationFilter
from .forms import SurveyFileAutomationForm
from .models import SurveyFileAutomation
from .tables import SurveyFileAutomationTable
from .tasks import *


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


class CreateSurveyFileAutomationView(SuccessMessageMixin, CreateView):
    model = SurveyFileAutomation
    form_class = SurveyFileAutomationForm
    template_name = 'surveyfiles/jxl_upload.html'
    success_url = reverse_lazy('surveyfiles:jxl_create_view')
    # success_url = '/success/'
    success_message = "%(file_name)s - %(site_no)s - %(utm_sr_name)s - %(scale_value)s was uploaded successfully !" \
                      " Please wait for QC emails"

    def get_form_kwargs(self):
        kwargs = super(CreateSurveyFileAutomationView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def form_invalid(self, form):
        print('form is not valid: {}'.format(self.get_context_data(form=form)))
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        print('validating form')
        print('user', self.request.user.username)
        print('call saving in form')
        form.save()
        print('saved in form successfully')
        print(self.request.FILES[u'document'])
        return super(CreateSurveyFileAutomationView, self).form_valid(form)

        # return self.render_to_response(self.get_context_data(
        #     form=form,
        #     uploaded_file=self.request.FILES[u'document']))

    def get_success_message(self, cleaned_data):
        print('cleaned data', cleaned_data)
        print('user id', self.request.user.id, type(self.request.user.id))
        uploader_usernane = self.request.user.username
        job_no = self.object.job_no
        site_no = self.object.site_no
        utm_sr_name = self.object.utm_sr_name
        scale_value = self.object.scale_value
        document_path = self.object.document.file.name
        document_name = os.path.basename(document_path)
        uploaded_time_str = self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S')
        args = (uploader_usernane, job_no, document_name, uploaded_time_str)
        notify_uploading.si(*args) \
            .set(queue='production') \
            .apply_async()
        # uploader = self.object.uploader
        # uploader_email = self.object.uploader_email
        # uploaded_time = self.object.uploaded_time.strftime('%Y-%m-%d %H:%M:%S')
        # project_manager = self.object.project_manager
        # project_manager_email = self.object.project_manager_email
        tracking_id = self.object.tracking_id

        # if self.object.create_data_report == 1 and os.path.basename(document_path)[-4:].lower() == '.jxl':

        if self.object.create_gis_data == 1:
            create_gis_data = True
        else:
            create_gis_data = False
            
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

        exporting_profiles = [int(item.strip()) for item in self.object.exporting_profile_no.split(',')
                              if len(item.strip()) > 0] \
            if self.object.exporting_profile_no != 'All Profiles' else self.object.exporting_profile_no

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

        args = (document_path, tracking_id, create_gis_data, create_client_report,
                exporting_types, exporting_profiles,
                overwriting, notify_surveyor, notify_pm, uploading_info)

        quality_check_jxl_task = quality_check_jxl.si(*args).set(queue='production')
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

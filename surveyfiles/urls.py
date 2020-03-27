from django.conf.urls import url, include

from .views import *
from django.contrib.auth.decorators import login_required

urlpatterns = [
    url('^list/', SurveyFilesListFilterView.as_view(), name='jxl_list_view'),
    url('^cards/', SurveyFilesCardsFilterView.as_view(), name='jxl_cards_view'),
    url('^sketch-setup/', login_required(JobSetUpView.as_view()), name='sketch_pdf_setup_view'),
    url('^data-export/', login_required(DataExportView.as_view()), name='data_export_view'),
    url('upload/', login_required(CreateSurveyFileAutomationView.as_view()), name='jxl_create_view'),
    url('ppp_automation/', login_required(CreatePPPFileAutomationView.as_view()), name='ppp_automation_view'),
]
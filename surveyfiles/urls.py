from django.conf.urls import url, include

from .views import *
from django.contrib.auth.decorators import login_required

urlpatterns = [
    url('^list/', SurveyFilesListFilterView.as_view(), name='jxl_list_view'),
    url('^cards/', SurveyFilesCardsFilterView.as_view(), name='jxl_cards_view'),
    url('upload/', login_required(CreateSurveyFileAutomationView.as_view()), name='jxl_create_view'),
]
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register('surveyfileautomation', SurveyFileAutomationViewSet, base_name='surveyfileautomation')
urlpatterns = router.urls

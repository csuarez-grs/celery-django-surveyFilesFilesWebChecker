# from django.utils.decorators import method_decorator
# from django.views.decorators.cache import cache_page
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from surveyfiles.models import SurveyFileAutomation
from .serializers import SurveyFileAutomationSerializer


class SurveyFileAutomationViewSet(viewsets.ModelViewSet):
    queryset = SurveyFileAutomation.objects.all()
    serializer_class = SurveyFileAutomationSerializer

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        return SurveyFileAutomation.objects \
            .exclude(qc_time__isnull=True) \
            .exclude(uploader__isnull=True) \
            .exclude(automation_ended__isnull=True)

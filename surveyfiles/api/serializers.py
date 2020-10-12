from rest_framework import serializers

from surveyfiles.models import SurveyFileAutomation


class SurveyFileAutomationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SurveyFileAutomation
        fields = (
            'url', 'tracking_id', 'document_name', 'job_no', 'site_no', 'uploader_name', 'surveyor_name',
            'total_qc_time', 'qc_passed', 'total_automation_time', 'automation_status', 'total_profiles',
            'total_points', 'total_structures', 'total_profiles_meters', 'create_gis_data',
            'create_client_report', 'exporting_types_selected', 'transmittals_folder')

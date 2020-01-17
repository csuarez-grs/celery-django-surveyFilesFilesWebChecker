import django_filters
from django.db import models

from .models import SurveyFileAutomation


class DynamicChoiceMixin(object):

    @property
    def field(self):
        queryset = self.parent.queryset
        field = super(DynamicChoiceMixin, self).field

        choices = list()
        have = list()
        # iterate through the queryset and pull out the values for the field name
        for item in queryset:
            field_value = getattr(item, self.field_name)
            if field_value in have:
                continue
            have.append(field_value)
            choices.append((field_value, field_value))
        field.choices.choices = sorted(choices)
        return field


class DynamicChoiceFilter(DynamicChoiceMixin, django_filters.ChoiceFilter):
    pass


class SurveyFileAutomationFilter(django_filters.FilterSet):

    uploader = DynamicChoiceFilter('uploader', empty_label='Select Uploader')
    project_manager = DynamicChoiceFilter('project_manager', empty_label='Select PM')
    automation_status = DynamicChoiceFilter('automation_status', empty_label='Automation Status')
    qc_passed = DynamicChoiceFilter('qc_passed', empty_label='QC Status')

    class Meta:
        model = SurveyFileAutomation
        fields = ['job_no', 'uploader', 'project_manager', 'automation_status', 'qc_passed']

        filter_overrides = {
            models.CharField: {
                'filter_class': django_filters.CharFilter,
                'extra': lambda f: {
                    'lookup_expr': 'contains',
                },
            },
        }

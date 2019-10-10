from django import forms

from new_fortis_tools_20190625 import read_jxl_info
from templatetags.auth_extras import *
from .models import SurveyFileAutomation, validate_jxl_pattern, exporting_types_options, \
    default_all_profiles_str, default_exporting_types_options

from SurveyFilesWebChecker.settings import logger_request
from django import forms

from SurveyFilesWebChecker.settings import logger_request
from new_fortis_tools_20190625 import read_jxl_info
from templatetags.auth_extras import *
from .models import SurveyFileAutomation, validate_jxl_pattern, exporting_types_options, \
    default_all_profiles_str, default_exporting_types_options


class SurveyFileAutomationForm(forms.ModelForm):
    # site_no = forms.DecimalField(required=True, min_value=1)
    # description = forms.CharField(widget=forms.Textarea(attrs={'rows': 5,
    #                                                            'placeholder': 'Simple Description'}),
    #                               required=False)
    notify_surveyor = forms.BooleanField(initial=False, required=False)
    notify_pm = forms.BooleanField(initial=False, required=False)
    create_gis_data = forms.BooleanField(initial=False, required=False)
    create_client_report = forms.BooleanField(initial=False, required=False)
    exporting_profile_no = forms.CharField(initial=default_all_profiles_str, required=False,
                                           label='Leave it as it is, or type Exporting Profile No, e.g. 1, 2, 5')
    exporting_types_selected = forms.MultipleChoiceField(choices=exporting_types_options,
                                                         initial=tuple(default_exporting_types_options),
                                                         widget=forms.widgets.CheckboxSelectMultiple,
                                                         required=False)
    overwriting = forms.BooleanField(initial=True, required=False)

    class Meta:
        model = SurveyFileAutomation
        fields = ['document', 'site_no', 'extract_input_values',
                  'utm_sr_name', 'scale_value',
                  'notify_surveyor', 'notify_pm',
                  'create_gis_data', 'create_client_report',
                  'exporting_profile_no',
                  'exporting_types_selected',
                  'overwriting']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(SurveyFileAutomationForm, self).__init__(*args, **kwargs)

        # if not is_automation_admin_group(self.user) and not self.user.is_superuser:
        #
        #     self.readonly_fields = [
        #         'notify_surveyor', 'notify_pm',
        #         'create_gis_data', 'create_client_report',
        #         'exporting_profile_no',
        #         'exporting_types_selected',
        #         'overwriting']
        #
        #     for field in self.readonly_fields:
        #         self.fields[field].widget = forms.HiddenInput()
        #         self.fields[field].label = False
        #         # if type(self.fields[field]) == forms.BooleanField:
        #         #     self.fields[field].initial = False
        #         # else:
        #         #     self.fields[field].initial = ''
        #         # print('Hiding {}, set to {}'.format(field, self.fields[field].initial))
        #
        #
        # else:
        #     self.readonly_fields = []

    def clean(self):
        cleaned_data = self.cleaned_data
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.user.username})
        document_name = str(cleaned_data['document'])
        logger_request.info('document name: {}'.format(document_name), extra={'username': self.user.username})
        extract_input_values = cleaned_data['extract_input_values']
        utm_sr_name = cleaned_data['utm_sr_name']
        scale_value = cleaned_data['scale_value']
        # print(document_name, type(document_name),
        #     extract_input_values, type(extract_input_values),
        #       utm_sr_name, type(utm_sr_name),
        #       scale_value, type(scale_value))
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.user.username})

        if (document_name[-4:].lower() == '.jxl' and not extract_input_values) \
                or document_name[-4:].lower() == '.csv':
            logger_request.info('Checking if UTM and scale are entered.', extra={'username': self.user.username})
            if utm_sr_name is None:
                self.add_error('utm_sr_name', 'Please select UTM name')
            if scale_value is None:
                self.add_error('scale_value', 'Please type scale factor')

        logger_request.info('cleaning is done', extra={'username': self.user.username})

        return cleaned_data

    # def clean_utm_sr_name(self):
    #     cleaned_data = self.cleaned_data
    #     if cleaned_data.get('document'):
    #         document = cleaned_data.get('document')
    #         document_path = document.file.name
    #         print('Reading from {}'.format(document_path))
    #         utm_sr_name, scale_value = read_jxl_info(document_path, return_utm_name=True)
    #         return utm_sr_name
    #     return None
    #
    # def clean_document(self):
    #     cleaned_data = self.cleaned_data
    #     if cleaned_data.get('document'):
    #         self.is_valid()

    # def is_valid(self):
    #     valid = super(JXLFileAutomationForm, self).is_valid()
    #     if not valid:
    #         return valid
    #
    #     cleaned_data = super(JXLFileAutomationForm, self).clean()
    #     if cleaned_data['document']:
    #         document = str(cleaned_data['document'])
    #         print('Document: {}'.format(document))
    #
    #         if document[-4:].lower() == '.csv':
    #             utm_sr_name = cleaned_data['utm_sr_name']
    #             scale_value = cleaned_data['scale_value']
    #             for item in [utm_sr_name, scale_value]:
    #                 if not item:
    #                     raise forms.ValidationError({'utm_sr_name': 'required for csv file',
    #                                                  'scale_value': 'required for csv file'})

    # def is_valid(self):
    #     print('cleaned data: {}'.format(self.cleaned_data))
    #     document = self.cleaned_data['document']
    #     document_path = document.file.name
    #     print('Reading {}'.format(document_path))
    #     if os.path.isfile(document_path):
    #         utm_sr_name, scale_value = read_jxl_info(document_path, return_utm_name=True)
    #         self.cleaned_data['utm_sr_name'] = utm_sr_name
    #         self.cleaned_data['scale_value'] = scale_value

    def save(self):
        logger_request.info('Start saving in form', extra={'username': self.user.username})
        user = self.user
        new_jxl_obj = super(SurveyFileAutomationForm, self).save(commit=False)
        document_path = str(new_jxl_obj.document.file.name)
        logger_request.info('Document path: {}'.format(document_path), extra={'username': self.user.username})
        document_name = os.path.basename(document_path)
        if document_name[-4:].lower() == '.jxl' and os.path.isfile(document_path):
            utm_sr, scale_value = read_jxl_info(document_path, return_utm_name=True)
            if new_jxl_obj.utm_sr_name is None and utm_sr is not None:
                new_jxl_obj.utm_sr_name = utm_sr
            if new_jxl_obj.scale_value is None and scale_value is not None:
                new_jxl_obj.scale_value = scale_value

        job_no = validate_jxl_pattern(new_jxl_obj.document)
        new_jxl_obj.job_no = job_no
        new_jxl_obj.uploader = user.username
        new_jxl_obj.uploader_email = user.email

        logger_request.info('Saving in form', extra={'username': self.user.username})
        new_jxl_obj.save()
        logger_request.info('Saving in form successfully', extra={'username': self.user.username})

        return new_jxl_obj

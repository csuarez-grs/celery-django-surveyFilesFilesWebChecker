from django import forms
import re
import os
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from SurveyFilesWebChecker.settings import logger_request
from new_fortis_tools_20190625 import read_jxl_info
from .models import SurveyFileAutomation, validate_jxl_pattern, exporting_types_options, \
    default_exporting_types_options, FORTIS_JOB_NO_PATTERN, FortisJobExtents, unit_report_type, PageNumsParser
import field_sketch_pdf

site_no_pattern = re.compile('Site_(\d+)\.gdb', re.IGNORECASE)


class SurveyFileAutomationForm(forms.ModelForm):
    # create_gis_data = forms.BooleanField(initial=True, required=False)
    # site_data_db = forms.CharField(required=False)
    exporting_types_selected = forms.MultipleChoiceField(choices=exporting_types_options,
                                                         initial=tuple(default_exporting_types_options),
                                                         widget=forms.widgets.CheckboxSelectMultiple,
                                                         required=False)

    class Meta:
        model = SurveyFileAutomation
        fields = ['document', 'site_no', 'extract_input_values',
                  'utm_sr_name', 'scale_value',
                  'create_gis_data',
                  'site_data_db',
                  'exporting_types_selected',
                  'skip_empty_pages',
                  'selected_pages',
                  'background_imagery',
                  'overwriting']
        help_texts = {
            'selected_pages': 'Please type certain page numbers for field sketch pdf.'
                              ' (Separated numbers by ",": 2,3,5. Or use pages range: 5-10).',
            'skip_empty_pages': 'If checked, only field sketch pages with survey data is produced.'
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(SurveyFileAutomationForm, self).__init__(*args, **kwargs)
        hidden_fields = ['create_gis_data', 'site_data_db']
        initial = kwargs.get('initial')
        if initial:
            self._use_reference = True
            hidden_fields += ['document', 'extract_input_values', 'utm_sr_name', 'scale_value']
        else:
            self._use_reference = False

        for field in hidden_fields:
                self.fields[field].disabled = True
                self.fields[field].widget = forms.HiddenInput()

        self.fields['extract_input_values'].required = False
        self.fields['extract_input_values'].initial = False
        self.fields['skip_empty_pages'].required = False
        self.fields['skip_empty_pages'].initial = True
        self.fields['overwriting'].required = False
        self.fields['overwriting'].initial = True
        self.fields['selected_pages'].widget.attrs['placeholder'] = '...2, 3, 9, 11-18...'

    def clean(self):
        cleaned_data = self.cleaned_data
        # logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.user.username})
        document = cleaned_data.get('document')
        # logger_request.info('document name: {}'.format(document_name), extra={'username': self.user.username})
        extract_input_values = cleaned_data['extract_input_values']
        utm_sr_name = cleaned_data['utm_sr_name']
        scale_value = cleaned_data['scale_value']
        # create_gis_data = bool(cleaned_data['create_gis_data'])
        # site_data_db = cleaned_data['site_data_db']
        exporting_types_selected = cleaned_data['exporting_types_selected']
        site_no = cleaned_data['site_no']
        selected_pages = cleaned_data['selected_pages']

        if re.search(FORTIS_JOB_NO_PATTERN, document.name):
            job_no = re.search(FORTIS_JOB_NO_PATTERN, document.name).groups()[0]
            sites = FortisJobExtents.get_sites(job_no)
            if site_no not in sites:
                self.add_error('site_no', 'Site {} is not set up in database yet ! Optional sites: {}'
                               .format(site_no, ', '.join([str(site) for site in sites])))

            try:
                all_pages_list = FortisJobExtents.get_page_nums(job_no, site_no)[1]

                if selected_pages:
                    pages_parser = PageNumsParser(selected_pages)
                    selected_pages_list = pages_parser.compile_nums_list()
                    incorrect_selected_pages = list(set(selected_pages_list) - set(all_pages_list))
                    if incorrect_selected_pages:
                        error = ValueError('{} not in site pages:\n{}'.format(incorrect_selected_pages,
                                                                              all_pages_list))
                        self.add_error('selected_pages', error)

            except ValidationError as e:
                self.add_error('site_no', e)

        if not self._use_reference and document:
            document_name = document.name
            if (document_name[-4:].lower() == '.jxl' and not extract_input_values) \
                    or document_name[-4:].lower() == '.csv':
                # logger_request.info('Checking if UTM and scale are entered.', extra={'username': self.user.username})
                if utm_sr_name is None:
                    self.add_error('utm_sr_name', 'Please select UTM name')
                if scale_value is None:
                    self.add_error('scale_value', 'Please type scale factor')

        logger_request.info('cleaning is done:\n{}'.format(cleaned_data), extra={'username': self.user.username})

        return cleaned_data

    def save(self):
        logger_request.info('Start saving in form', extra={'username': self.user.username})
        user = self.user
        new_jxl_obj = super(SurveyFileAutomationForm, self).save(commit=False)
        document_path = str(new_jxl_obj.document.file.name)
        logger_request.info('Document path: {}'.format(document_path), extra={'username': self.user.username})
        document_name = os.path.basename(document_path)
        if document_name[-4:].lower() == '.jxl' and os.path.isfile(document_path):
            try:
                utm_sr, scale_value = read_jxl_info(document_path, return_utm_name=True)[0:2]
                if new_jxl_obj.utm_sr_name is None and utm_sr is not None:
                    new_jxl_obj.utm_sr_name = utm_sr
                if new_jxl_obj.scale_value is None and scale_value is not None:
                    new_jxl_obj.scale_value = scale_value
            except Exception as e:
                logger_request.warning('Failed to extract utm and scale from {}:\n{}'.format(document_path, str(e)),
                                       extra={'username': self.user.username})

        job_no = validate_jxl_pattern(new_jxl_obj.document)
        new_jxl_obj.job_no = job_no
        new_jxl_obj.uploader = user.username
        new_jxl_obj.uploader_name = '{} {}'.format(user.first_name, user.last_name)
        new_jxl_obj.uploader_email = user.email

        exporting_types = [item.strip() for item in new_jxl_obj.exporting_types_selected
                           if len(item.strip()) > 0]

        if new_jxl_obj.site_data_db:
            new_jxl_obj.create_gis_data = False
        else:
            new_jxl_obj.create_gis_data = True

        if len(exporting_types) > 0:
            new_jxl_obj.create_client_report = True
        else:
            new_jxl_obj.create_client_report = False

        new_jxl_obj.raise_invalid_errors = False  # model still has this field, so make it False since it is not
        # allowed to insert Null to Boolean field

        logger_request.info('Saving in form', extra={'username': self.user.username})
        new_jxl_obj.save()
        logger_request.info('Saving in form successfully', extra={'username': self.user.username})

        return new_jxl_obj


def validate_emails(text):
    items = [str(item).strip() for item in re.split('[,;\s]+', text) if len(str(item).strip()) > 0]
    email_pattern = re.compile('^[a-zA-Z0-9]+@[a-zA-Z0-9\.]+$')
    any_errors = [item for item in items if not re.match(email_pattern, item)]
    if any_errors:
        raise forms.ValidationError('{} is not valid emails!'.format(', '.join(any_errors)))


class DataExportForm(forms.Form):
    site_db_path = forms.CharField(label='Site GeoDatabase Path', max_length=500)
    site_no = forms.IntegerField(label='Site No (In case all sites data are created in the above single geodatabase !)',
                                 required=False)
    source_jxl_path = forms.CharField(label='Source JXL Path', max_length=500, required=False)
    # exports = [field_sketch_pdf_type]
    # exports_options = [(item, item) for item in exports]

    exporting_types_selected = forms.MultipleChoiceField(choices=exporting_types_options,
                                                         initial=tuple(default_exporting_types_options),
                                                         widget=forms.widgets.CheckboxSelectMultiple,
                                                         required=False)

    background_imagery = forms.ChoiceField(label='Background Imagery',
                                           choices=((item, item.split('\\')[1])
                                                    for item in field_sketch_pdf.IMAGERY_CHOICES),
                                           initial=field_sketch_pdf.VALTUS_IMAGERY)

    overwriting = forms.BooleanField(label='Overwriting', initial=False, required=False)
    contact_emails = forms.CharField(label='Contact Emails (Separated by "," or ";")', required=False, max_length=255,
                                     validators=[validate_emails])

    def __init__(self, *args, **kwargs):
        print('form kwargs: {}'.format(kwargs))
        self.user = kwargs.pop('user')
        super(DataExportForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.user.username})

        exporting_types_selected = self.cleaned_data.get('exporting_types_selected')

        source_jxl_path = self.cleaned_data.get('source_jxl_path')
        if source_jxl_path is not None and len(source_jxl_path.strip()) > 0:
            if not os.path.isfile(source_jxl_path) or source_jxl_path[-4:].lower() != '.jxl':
                raise forms.ValidationError(
                    _('Please provide valid jxl path !!!')
                )

            elif not re.search(FORTIS_JOB_NO_PATTERN, os.path.basename(source_jxl_path)):
                raise forms.ValidationError(
                    _('No Fortis job "xxxFxxxx" found in jxl file name !!!')
                )
        else:
            source_jxl_path = None
            self.cleaned_data['source_jxl_path'] = None
            if unit_report_type in exporting_types_selected:
                raise forms.ValidationError('Please type JXL file path for exporting unit report pdf.')

        site_db_path = self.cleaned_data.get('site_db_path')
        if site_db_path is not None:
            if not os.path.isdir(site_db_path) or site_db_path[-4:].lower() != '.gdb':
                raise forms.ValidationError(
                    _('Please provide valid geodatabase path !!!')
                )

            site_db_name = os.path.basename(site_db_path)
            if not re.search(FORTIS_JOB_NO_PATTERN, site_db_name):
                raise forms.ValidationError(
                    _('No Fortis job "xxxFxxxx" found in geodatabase name')
                )

            if not re.search(site_no_pattern, site_db_name):
                raise forms.ValidationError(
                    _('No "Site_xx" found in geodatabase name')
                )

            site_db_path = site_db_path.replace('R:', r'\\grs.com\DFS\JOBS')
            self.cleaned_data['site_db_path'] = site_db_path

        if site_db_path is not None and os.path.isdir(site_db_path) and source_jxl_path is not None \
                and os.path.isfile(source_jxl_path):
            site_db_job_no = re.search(FORTIS_JOB_NO_PATTERN, os.path.basename(site_db_path)).groups()[0]
            jxl_job_no = re.search(FORTIS_JOB_NO_PATTERN, os.path.basename(source_jxl_path)).groups()[0]
            if site_db_job_no.upper() != jxl_job_no.upper():
                raise forms.ValidationError(
                    _('Site db job no {} is not the same as jxl job no {}'.format(site_db_job_no, jxl_job_no))
                )

        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.user.username})

        logger_request.info('cleaning is done', extra={'username': self.user.username})

        return cleaned_data


class PPPFileAutomationForm(forms.ModelForm):
    class Meta:
        model = SurveyFileAutomation
        fields = ['document', 'site_no', 'extract_input_values', 'utm_sr_name', 'scale_value',
                  'target_field_folder', 'site_data_db',
                  'overwriting']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(PPPFileAutomationForm, self).__init__(*args, **kwargs)
        self.fields['utm_sr_name'].required = False
        self.fields['scale_value'].required = True
        self.fields['site_data_db'].required = False
        self.fields['target_field_folder'].required = True
        self.fields['overwriting'].required = False
        self.fields['overwriting'].initial = False
        self.fields['extract_input_values'].required = False
        self.fields['extract_input_values'].initial = True

    def clean(self):
        cleaned_data = self.cleaned_data
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.user.username})
        document_name = str(cleaned_data['document'])
        site_data_db = self.cleaned_data.get('site_data_db')
        target_field_folder = self.cleaned_data.get('target_field_folder')
        extract_input_values = cleaned_data['extract_input_values']
        utm_sr_name = cleaned_data['utm_sr_name']
        scale_value = cleaned_data['scale_value']

        if document_name[-4:].lower() == '.jxl' and not extract_input_values:
            logger_request.info('Checking if utm and scale value are entered.', extra={'username': self.user.username})
            if utm_sr_name is None:
                raise forms.ValidationError(
                    _('Please check "Extract UTM names check box or manually select UTM from dropdown list !!!')
                )

        if document_name[-4:].lower() == '.csv':
            logger_request.info('Checking if utm and scale value are entered.', extra={'username': self.user.username})
            if utm_sr_name is None or scale_value is None:
                raise forms.ValidationError(
                    _('Please manually select UTM from dropdown list and type scale value !!!')
                )

        if target_field_folder is not None:
            target_field_folder = target_field_folder.replace('R:', r'\\grs.com\DFS\JOBS')
            self.cleaned_data['target_field_folder'] = target_field_folder

        logger_request.info('document name: {}'.format(document_name), extra={'username': self.user.username})
        logger_request.info('target field folder: {}'.format(target_field_folder),
                            extra={'username': self.user.username})
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.user.username})

        document_job_no = re.search(FORTIS_JOB_NO_PATTERN, document_name).groups()[0]
        for item in [target_field_folder, site_data_db]:
            if item and re.search(FORTIS_JOB_NO_PATTERN, os.path.basename(item)):
                item_job_no = re.search(FORTIS_JOB_NO_PATTERN, os.path.basename(item)).groups()[0]
                if document_job_no.upper() != item_job_no.upper():
                    raise forms.ValidationError(
                        '{} has job no {} (Different from {}) in document file !!!'
                            .format(item, item_job_no, document_job_no)
                    )

        logger_request.info('cleaning is done', extra={'username': self.user.username})

        return cleaned_data

    def save(self):
        logger_request.info('Start saving in form', extra={'username': self.user.username})
        user = self.user
        new_jxl_obj = super(PPPFileAutomationForm, self).save(commit=False)
        document_path = str(new_jxl_obj.document.file.name)
        logger_request.info('Document path: {}'.format(document_path), extra={'username': self.user.username})

        document_name = os.path.basename(document_path)
        if document_name[-4:].lower() == '.jxl' and os.path.isfile(document_path):
            try:
                utm_sr, scale_value = read_jxl_info(document_path, return_utm_name=True)[0:2]
                if new_jxl_obj.utm_sr_name is None and utm_sr is not None:
                    new_jxl_obj.utm_sr_name = utm_sr
            except Exception as e:
                logger_request.warning('Failed to extract utm from {}:\n{}'.format(document_path, str(e)),
                                       extra={'username': self.user.username})

        jxl_job_no = validate_jxl_pattern(new_jxl_obj.document)

        new_jxl_obj.job_no = jxl_job_no
        new_jxl_obj.uploader = user.username
        new_jxl_obj.uploader_name = '{} {}'.format(user.first_name, user.last_name)
        new_jxl_obj.uploader_email = user.email

        logger_request.info('Saving in form', extra={'username': self.user.username})
        new_jxl_obj.save()
        logger_request.info('Saving in form successfully', extra={'username': self.user.username})

        return new_jxl_obj


class JobSetUpForm(forms.Form):
    job_no = forms.CharField(label='Fortis Job No', max_length=8)
    selected_sites = forms.CharField(label='Selected Sites (separated by ",") or leave blank for all sites'
                                           ' retrieved from database', max_length=50, required=False)
    background_imagery = forms.ChoiceField(label='Background Imagery',
                                           choices=((item, item.split('\\')[1])
                                                    for item in field_sketch_pdf.IMAGERY_CHOICES),
                                           initial=field_sketch_pdf.VALTUS_IMAGERY)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(JobSetUpForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        logger_request.info('cleaned data: {}'.format(cleaned_data), extra={'username': self.user.username})
        job_no = str(cleaned_data['job_no']).strip()
        selected_sites = [item.strip() for item in str(cleaned_data['selected_sites']).strip().split(',')
                          if len(item.strip()) > 0]

        if not re.match(FORTIS_JOB_NO_PATTERN, job_no):
            raise forms.ValidationError('{} is not Fortis job pattern !!!'.format(job_no))

        if selected_sites and any([not re.match('^\d+$', item) for item in selected_sites]):
            raise forms.ValidationError('Selected sites only allow integer separated by ","')

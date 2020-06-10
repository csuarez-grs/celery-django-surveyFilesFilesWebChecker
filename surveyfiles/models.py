# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
import re
import time
import uuid

from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models

from SurveyFilesWebChecker.settings import logger_model

# Create your models here.
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from multiselectfield import MultiSelectField

from core.models import GRSJobInfo

from new_fortis_tools_20190625 import project_coordinates_list, default_exporting_types, read_jxl_info, \
    parse_surveyor_from_file_name, field_sketch_pdf_type, unit_report_type

fortis_job_no_pattern = re.compile('(?P<job_no>\d{2}[CEM]F\d{4})', re.IGNORECASE)

exporting_types_options = [(item, item) for item in default_exporting_types]
default_exporting_types_options = [unit_report_type, field_sketch_pdf_type]
default_all_profiles_str = 'All Profiles'
project_coordinates_choices = ((item, item) for item in project_coordinates_list)

min_scale_value = 0.0
max_scale_value = 1.5


def validate_site_data_db(site_data_db):
    if not os.path.isdir(site_data_db):
        raise ValidationError(
            _('%(site_data_db)s is not valid folder !!!'),
            params={'site_data_db': site_data_db}
        )
    elif len(os.listdir(site_data_db)) == 0:
        raise ValidationError(
            _('%(site_data_db)s is empty folder !!!'),
            params={'site_data_db': site_data_db}
        )
    elif not re.search(fortis_job_no_pattern, os.path.basename(site_data_db)):
        raise ValidationError(
            _('%(site_data_db)s has no valid fortis job no !!!'),
            params={'site_data_db': os.path.basename(site_data_db)}
        )


def validate_target_field_folder(target_field_folder):
    if not os.path.isdir(target_field_folder):
        raise ValidationError(
            _('%(target_field_folder)s is not valid folder !!!'),
            params={'target_field_folder': target_field_folder}
        )
    elif len(os.listdir(target_field_folder)) == 0:
        raise ValidationError(
            _('%(target_field_folder)s is empty folder !!!'),
            params={'target_field_folder': target_field_folder}
        )
    elif not re.search(fortis_job_no_pattern, os.path.basename(target_field_folder)):
        raise ValidationError(
            _('%(target_field_folder)s has no valid fortis job no !!!'),
            params={'target_field_folder': os.path.basename(target_field_folder)}
        )
    # else:
    #     sub_dirs = [os.path.join(target_field_folder, item) for item in os.listdir(target_field_folder)
    #                 if os.path.isdir(os.path.join(target_field_folder, item))]
    #     notes_sub_folders = [item for item in sub_dirs if os.path.basename(item).title() == 'Notes']
    #     photo_sub_folders = [item for item in sub_dirs if re.search('Photo|Picture', os.path.basename(item),
    #                                                                 re.IGNORECASE)]
    #
    #     if len(notes_sub_folders) != 1:
    #         raise ValidationError(
    #             _('%(count)s Notes folder(s) found !!!'),
    #             params={'count': len(notes_sub_folders)}
    #         )
    #
    #     if len(photo_sub_folders) != 1:
    #         raise ValidationError(
    #             _('%(count)s Photos or Pictures folder(s) found !!!'),
    #             params={'count': len(photo_sub_folders)}
    #         )


def validate_jxl_content(document):
    document_path = str(document.file.name)
    document_name = os.path.basename(document_path)
    document_ext = document_name[-4:].lower()

    if document_ext == '.jxl':

        try:
            read_jxl_info(document_path, return_utm_name=True)
        except Exception as e:
            errors = str(e)
            raise ValidationError(
                _('%(document_name)s errors: %(errors)s'),
                params={'document_name': document_name, 'errors': errors}
            )


def validate_jxl_pattern(document):
    document_name = os.path.basename(str(document.file.name))
    document_ext = document_name[-4:].lower()
    logger_model.info('checking {}: type-{} ext-{}'.format(document_name, type(document_name), document_ext))

    if document_ext not in ['.csv', '.jxl']:
        raise ValidationError(
            _('%(file_name)s: is not .csv or .jxl file'),
            params={'file_name': document_name},
        )

    # jxl_name_pattern = re.compile('(?P<job_no>\d{2}[CEM]F\d{4})\-S(?P<site_no>\d+)[\_\-\.]', re.IGNORECASE)
    if not re.search(fortis_job_no_pattern, document_name):
        raise ValidationError(
            # _('%(file_name)s: Please include valid job no and site no like "19CF0001-S1" in your file name'),
            _('%(file_name)s: Please include valid job no like "19CF0001" in your file name'),
            params={'file_name': document_name},
        )
    else:
        group_matched = list(re.finditer(fortis_job_no_pattern, document_name))[0]
        groups_dict = group_matched.groupdict()
        logger_model.info('{}'.format(groups_dict))

    job_no = groups_dict['job_no']
    # site_no = int(groups_dict['site_no'])

    try:
        GRSJobInfo.objects.get(jobnumber=job_no)
    except GRSJobInfo.DoesNotExist:
        raise ValidationError(
            _('%(job_no)s is not valid latitude job'),
            params={'job_no': job_no}
        )

    return job_no


def get_upload_path(instance, filename):
    return os.path.join('documents',
                        datetime.date.today().strftime('%Y-%m-%d'),
                        instance.uploader,
                        time.strftime('%H-%M-%S'),
                        filename)


def get_obj_time_ago(obj_time):
    if datetime.date.today() == obj_time.date():
        delta = datetime.datetime.now() - obj_time
    else:
        delta = datetime.date.today() - obj_time.date()

    seconds = int(round(delta.total_seconds()))
    if seconds < 0:
        seconds = 0

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if days > 0:
        time_str = '{} days'.format(days)
    elif hours > 0:
        time_str = '{} hours'.format(hours)
    elif minutes > 0:
        time_str = '{} minutes'.format(minutes)
    else:
        time_str = "{:02d} seconds".format(seconds)

    return time_str


def get_target_url(target_path, name=None):
    if target_path is not None and re.search(r'grs\.com', target_path, re.IGNORECASE):
        if os.path.isdir(target_path) or os.path.isfile(target_path):
            target_url = 'file://{}'.format(target_path[2:])
            if name is None:
                if os.path.isdir(target_path):
                    target_url_link = format_html(
                        '<a href="{0}">{1}</a>'.format(target_url, os.path.basename(target_path)))
                else:
                    target_url_link = format_html('<a href="{0}">{1}</a>'.format(target_url,
                                                                                 os.path.basename(target_path)[
                                                                                 0:-4].replace('-', '_')))
            else:
                target_url_link = format_html('<a href="{0}">{1}</a>'.format(target_url, name))
        else:
            target_url_link = 'File does not exits anymore'

    else:
        target_url_link = None

    return target_url_link


class OverwriteStorage(FileSystemStorage):
    '''
    Muda o comportamento padrão do Django e o faz sobrescrever arquivos de
    mesmo nome que foram carregados pelo usuário ao invés de renomeá-los.
    '''

    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            os.remove(os.path.join(self.location, name))
        return name


class MinMaxFloat(models.FloatField):
    def __init__(self, min_value=None, max_value=None, *args, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(MinMaxFloat, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value': self.max_value}
        defaults.update(kwargs)
        return super(MinMaxFloat, self).formfield(**defaults)


class MinMaxInteger(models.IntegerField):
    def __init__(self, min_value=None, max_value=None, *args, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(MinMaxInteger, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value': self.max_value}
        defaults.update(kwargs)
        return super(MinMaxInteger, self).formfield(**defaults)


class SurveyFileAutomation(models.Model):
    _DATABASE = 'default'
    tracking_id = models.CharField(db_column='Tracking ID', primary_key=True, max_length=36)
    job_no = models.CharField(db_column='GRSJobNo', max_length=30)
    description = models.CharField(verbose_name='Description', max_length=500, blank=True, null=True)
    document = models.FileField(upload_to=get_upload_path,
                                verbose_name='Document',
                                blank=False, null=False,
                                validators=[validate_jxl_pattern],
                                storage=OverwriteStorage())
    site_no = MinMaxInteger(db_column='Site No', blank=False, null=False, min_value=1)
    extract_input_values = models.BooleanField(verbose_name='Extract UTM name and scale factor value from jxl file',
                                               default=False, blank=False, null=False)
    utm_sr_name = models.CharField(verbose_name='Project System Name', max_length=100, blank=True, null=True,
                                   choices=project_coordinates_choices)
    scale_value = MinMaxFloat(verbose_name='Scale Value', blank=True, null=True,
                              min_value=min_scale_value, max_value=max_scale_value)
    raise_invalid_errors = models.BooleanField(db_column='Raise Invalid Errors',
                                               verbose_name='Raise Invalid Profile Connection Errors',
                                               default=True, blank=False, null=False,
                                               help_text='Raise Invalid Profile Connection Errors')
    site_data_db = models.CharField(db_column='Site Data DB', max_length=500, blank=True, null=True,
                                    validators=[validate_site_data_db],
                                    help_text=r'Paste one valid site db to skip "create gis data"'
                                                         ' if you already have GIS data created'
                                              r' (\\grs.com\DFS\GIS\GIS_Working\JXL_Web_Job_Root\Dev\jxue'
                                              r'\20MF0041\CADD\Mapping\01_Data\Site_1\20MF0041_Site_1.gdb)')
    create_gis_data = models.BooleanField(db_column='Create GIS datasets',
                                          verbose_name='Create GIS datasets',
                                          default=False, blank=False, null=False)
    notify_surveyor = models.BooleanField(db_column='Send QC results to Surveyor',
                                          default=False, blank=False, null=False)
    notify_pm = models.BooleanField(db_column='Send Client Reports to Project Manager',
                                    default=False, blank=False, null=False)
    create_client_report = models.BooleanField(db_column='Create Client Report',
                                               verbose_name='Create Client Report',
                                               default=False, blank=False, null=False)
    exporting_types_selected = MultiSelectField(db_column='Select Export Types', max_length=255,
                                                choices=exporting_types_options,
                                                default=default_exporting_types_options,
                                                verbose_name='Select Export Types')
    exporting_profile_no = models.CharField(db_column='Type Exporting Profile No',
                                            max_length=255,
                                            verbose_name='Leave it as it is, or type Exporting Profile No, e.g. 1, 2, 5',
                                            blank=False, null=False, default=default_all_profiles_str)
    overwriting = models.BooleanField(verbose_name='Overwritting existing data',
                                      default=True, blank=False, null=False)
    uploaded_time = models.DateTimeField(verbose_name='Uploaded Time', blank=False, null=False)
    uploader = models.CharField(max_length=30, verbose_name='Uploader', blank=False, null=False)
    uploader_name = models.CharField(max_length=50, verbose_name='Uploader Name', blank=True, null=True)
    uploader_email = models.EmailField(max_length=50, verbose_name='Uploader Email', blank=False, null=False)
    job_description = models.CharField(db_column='Job Description', max_length=500, blank=True, null=True)
    project_manager = models.CharField(db_column='Project Manager', max_length=50, blank=True, null=True)
    project_manager_email = models.CharField(db_column='Project Manager Email', max_length=50, blank=True, null=True)
    surveyor_name = models.CharField(db_column='Surveyor', max_length=50, blank=True, null=True)
    surveyor_email = models.CharField(db_column='Surveyor Email', max_length=50, blank=True, null=True)
    qc_time = models.DateTimeField(verbose_name='Check Time', blank=True, null=True)
    qc_passed = models.CharField(verbose_name='QC Passed', max_length=30, blank=True, null=True)
    jxl_errors = models.CharField(max_length=500, verbose_name='JXL Errors', blank=True, null=True)
    site_folder = models.CharField(db_column='Site Folder', max_length=500, blank=True, null=True)
    automation_started = models.DateTimeField(db_column='Automation Started', blank=True, null=True)
    automation_ended = models.DateTimeField(db_column='Automation Ended', blank=True, null=True)
    time_cost_minutes = models.IntegerField(db_column='Time Cost Minutes', blank=True, null=True)
    automation_status = models.CharField(db_column='Automation Status', max_length=10, blank=True, null=True)
    log_path = models.CharField(db_column='Log Path', max_length=255, blank=True, null=True,
                                verbose_name='Working Log')
    exp_path = models.TextField(db_column='EXP Path', blank=True, null=True)
    ald_csv_path = models.TextField(db_column='ALD CSV Path', blank=True, null=True)
    wgs84_csv = models.TextField(db_column='WGS84 CSV', blank=True, null=True)
    kmz_path = models.TextField(db_column='KMZ Path', blank=True, null=True)
    unit_report_path = models.TextField(db_column='Unit Report', blank=True, null=True)
    errors = models.CharField(db_column='Errors', max_length=500, blank=True, null=True)
    target_field_folder = models.CharField(db_column='Target Field Folder', max_length=255, blank=True, null=True,
                                           validators=[validate_target_field_folder],
                                           help_text=r'Paste a valid field folder path like '
                                                     r'\\grs.com\DFS\Jobs\2019\_Edmonton'
                                                     r'\19EF0397\Data & Calcs\1-Field Returns\20191227 AC\19EF0397'
                                                     r' AC 20191227 S1 CANNET')
    transmittals_folder = models.CharField(db_column='Transmittals Folder', max_length=255, blank=True, null=True)
    done_with_automation = models.CharField(db_column='Done With Automation', max_length=1
                                            , blank=True, null=True,
                                            choices=(('Y', 'Yes'), ('N', 'No'), ('', 'Blank')))
    edited_time = models.DateTimeField(db_column='Edited Time', blank=True, null=True)
    edited_by = models.CharField(db_column='Edited By', max_length=50, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'SurveyFileAutomation'
        ordering = ('-uploaded_time', 'job_no')

    def __unicode__(self):
        return '{} - {} - {}'.format(self.uploaded_time, self.uploader, self.document.path)

    @property
    def latest_log_time(self):
        if self.log_path is not None and os.path.isfile(self.log_path):
            line_time_str_pattern = re.compile('^\d{4}-(\d{2}-\d{2}\s\d{2}:\d{2}):\d{2}\s')
            try:
                with open(self.log_path) as reader:
                    lines = reader.readlines()
                    lines_with_time = [line for line in lines if re.match(line_time_str_pattern, line)]
                    if len(lines_with_time) == 0:
                        return None
                    last_line = lines_with_time[-1]
                    last_time = re.search(line_time_str_pattern, last_line).groups()[0]
                    return datetime.datetime.strptime(last_time, '%m-%d %H:%M').strftime('%H:%M on %b %d')
            except Exception as e:
                logger_model.exception(e)
                return None
        else:
            return None

    @property
    def automation_type(self):
        if self.target_field_folder is not None:
            return 'PPP Automation'
        else:
            return 'QC & Automation'

    @property
    def total_automation_time(self):
        if self.automation_started is not None:
            if self.automation_ended is not None:
                running_end_time = self.automation_ended
                pre_text = 'Cost'
            else:
                running_end_time = datetime.datetime.now()
                pre_text = 'Running'
        else:
            return 'Not started'

        total_running_seconds = int((running_end_time - self.automation_started).total_seconds())
        if total_running_seconds < 60:
            total_running_time = '{} {} seconds'.format(pre_text, total_running_seconds)
        else:
            total_running_time = '{} {} minutes'.format(pre_text, total_running_seconds / 60)

        return total_running_time

    @property
    def total_qc_time(self):
        if self.uploaded_time is not None and self.qc_time is not None:
            if self.qc_passed is None:
                running_start_time = self.qc_time
                running_end_time = datetime.datetime.now()
                pre_text = 'Running'
            else:
                running_start_time = self.uploaded_time
                running_end_time = self.qc_time
                pre_text = 'Cost'
        else:
            return 'Not started'

        total_running_seconds = int((running_end_time - running_start_time).total_seconds())
        if total_running_seconds < 60:
            total_running_time = '{} {} seconds'.format(pre_text, total_running_seconds)
        else:
            total_running_time = '{} {} minutes'.format(pre_text, total_running_seconds / 60)

        return total_running_time

    def save(self, *args, **kwargs):

        if self._state.adding:
            job_no = self.job_no
            self.tracking_id = str(uuid.uuid1())
            self.uploaded_time = datetime.datetime.now()

            if job_no is not None:
                job_obj = GRSJobInfo.objects.get(jobnumber=job_no)
                if job_obj is not None:
                    self.project_manager = job_obj.get_pm_name()
                    self.project_manager_email = job_obj.get_pm_email()
                    try:
                        self.job_description = job_obj.description.encode(
                            'utf-8') if job_obj.description is not None else None
                    except:
                        self.job_description = None

            if self.document.path is not None:
                try:
                    file_date, job_no, surveyor_init, surveyor_name, surveyor_email \
                        = parse_surveyor_from_file_name(self.document.path)
                    if surveyor_name is None:
                        file_date, job_no, surveyor_init, surveyor_name, surveyor_email \
                            = parse_surveyor_from_file_name(self.target_field_folder)
                    self.surveyor_name = surveyor_name
                    self.surveyor_email = surveyor_email
                except Exception as e:
                    logger_model.exception('Failed to extract surveyor from {}: {}'
                                           .format(os.path.basename(self.document.path), e))

        super(SurveyFileAutomation, self).save(*args, **kwargs)

    def get_log_link(self):
        if self.log_path is not None and os.path.isfile(self.log_path):
            log_link = get_target_url(self.log_path, name='log')
            return log_link
        else:
            return None

    def get_survey_file_link(self):
        if self.document is not None and os.path.isfile(self.document.path):
            document_unc_path = self.document.path.replace('T:', r'\\grs.com\DFS\GIS')
            document_link = get_target_url(document_unc_path)
            return document_link
        else:
            return None

    def get_field_folder_link(self):
        if self.target_field_folder is not None and os.path.isdir(self.target_field_folder):
            field_folder_link = get_target_url(self.target_field_folder,
                                               os.path.basename(self.target_field_folder).replace(' ', '_'))
            return field_folder_link
        else:
            return None

    def get_site_folder_link(self):
        if self.site_folder is not None and os.path.isdir(self.site_folder):
            folder_link = get_target_url(self.site_folder)
        else:
            folder_link = None

        return folder_link

    def get_time_ago(self):
        return get_obj_time_ago(self.uploaded_time)

    def get_exp_links(self):

        file_list = [str(item).strip() for item in self.exp_path.split('; ')
                     if os.path.isfile(str(item).strip())]

        if len(file_list) > 0:
            links_str = format_html(' '.join(sorted([get_target_url(item) for item in file_list])))
        else:
            links_str = None

        return links_str

    def get_ald_csv_links(self):

        file_list = [str(item).strip() for item in self.ald_csv_path.split('; ')
                     if os.path.isfile(str(item).strip())]

        if len(file_list) > 0:
            links_str = format_html(' '.join(sorted([get_target_url(item) for item in file_list])))
        else:
            links_str = None

        return links_str

    def get_wgs_84_csv_link(self):
        if self.wgs84_csv is not None and os.path.isfile(self.wgs84_csv):
            file_link = get_target_url(self.wgs84_csv)
        else:
            file_link = None
        return file_link

    def get_kmz_link(self):
        if self.kmz_path is not None and os.path.isfile(self.kmz_path):
            file_link = get_target_url(self.kmz_path)
        else:
            file_link = None
        return file_link

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
import re
import traceback

from django.db import models
from django.utils.html import format_html


# import core_tools

# Create your models here.


def get_job_folder_url(job_folder):
    folder_mapping = {
        'S': r'\\grs.com\DFS\Municipal',
        'R': r'\\grs.com\DFS\Jobs'
    }

    job_folder_reformatted = None

    if re.match('^[A-Z]:', job_folder, re.IGNORECASE):
        drive_letter = job_folder[0].upper()
        # print drive_letter
        if drive_letter in folder_mapping.keys():

            job_folder_reformatted = '{}\{}'.format(folder_mapping[drive_letter], job_folder[3:])

            if not os.path.isdir(job_folder_reformatted):
                job_folder_reformatted = None

    if job_folder_reformatted is not None:
        job_folder_url = 'file://{}'.format(job_folder_reformatted[2:])
        job_folder_url_link = format_html(
            '<a href="{0}">{1}</a>'.format(job_folder_url, '{} Folder'.format(os.path.basename(job_folder_reformatted))))
        job_folder_full_url_link = format_html('<a href="{0}">{1}</a>'.format(job_folder_url, job_folder_reformatted))
    else:
        job_folder_url_link = None
        job_folder_full_url_link = None

    return job_folder_url_link, job_folder_full_url_link


class GRSJobInfoManager(models.Manager):
    def get_queryset(self):
        return super(GRSJobInfoManager, self).get_queryset() \
            .filter(jobdate__gte=datetime.datetime.strptime('2010-01-01', '%Y-%m-%d'),
                    jobnumber__isnull=False) \
            .extra(where=["(len(jobnumber) between 6 and 8) and isnumeric(substring(jobnumber, 1, 2)) = 1 and "
                          "isnumeric(substring(reverse(jobnumber), 1, 3)) = 1"])


class GRSJobInfo(models.Model):
    _DATABASE = 'latidatasql'

    jobnumber = models.CharField(db_column='JobNumber', max_length=20, primary_key=True, verbose_name='Job Number')
    jobdate = models.DateTimeField(db_column='Jobdate', blank=True, null=True, verbose_name='Job Date')
    description = models.CharField(db_column='Description', max_length=255, blank=True, null=True, verbose_name='Description')
    filenumber = models.CharField(db_column='FileNumber', max_length=50, blank=True, null=True, verbose_name='File Number')
    workstatus = models.CharField(db_column='WorkStatus', max_length=50, blank=True, null=True, verbose_name='Work Status')
    specialdetails = models.TextField(db_column='SpecialDetails', blank=True, null=True, verbose_name='Special Details')
    txtclientrefno = models.CharField(db_column='txtClientRefNo', max_length=50, blank=True, null=True,
                                      verbose_name='Client Info')
    company_name = models.CharField(db_column='Company Name', max_length=100, blank=True, null=True, verbose_name='Client')
    jobcaptain = models.CharField(db_column='JobCaptain', max_length=50, blank=True, null=True, verbose_name='Project Manager')

    objects = GRSJobInfoManager()

    def latitude_job_folder(self):
        latitude_folder = Tbljobs.objects.get(job_number=self.jobnumber).jobfolder

        return get_job_folder_url(latitude_folder)[0]

    def latitude_job_folder_full_path(self):
        latitude_folder = Tbljobs.objects.get(job_number=self.jobnumber).jobfolder

        return get_job_folder_url(latitude_folder)[1]

    def getPID(self, mer, twp, rge, sec, qtr=None, lsd=None):
        try:
            if int(mer) not in range(1, 7):
                raise Exception("'{0}' is not in range '{1}'".format(mer, "(1,6)"))
            elif int(twp) not in range(1, 128):
                raise Exception("'{0}' is not in range '{1}'".format(twp, "(1,127)"))
            elif int(rge) not in range(1, 35):
                raise Exception("'{0}' is not in range '{1}'".format(rge, "(1,34)"))

            if sec is not None:
                secStr = str(sec)
                goodSecList = []
                if re.search("[,&]", secStr):
                    secList = re.split("[,&]", secStr)
                    secListCleaned = [item.strip() for item in secList]
                    for item in secListCleaned:
                        if re.search("-", item):
                            secPath = item.split("-")
                            secPathSorted = [int(item) for item in secPath]
                            secPathSorted.sort()
                            secStart = secPathSorted[0]
                            secEnd = secPathSorted[1]
                            secListBuild = [item for item in range(secStart, secEnd + 1)]
                            goodSecList.extend(secListBuild)
                else:
                    if re.search("-", secStr):
                        secPath = secStr.split("-")
                        secPathSorted = [int(item) for item in secPath]
                        secPathSorted.sort()
                        secStart = secPathSorted[0]
                        secEnd = secPathSorted[1]
                        goodSecList = [item for item in range(secStart, secEnd + 1)]
                    else:
                        goodSecList = [sec]
                goodSecListUnique = set([int(item) for item in goodSecList])
                if any(item not in range(1, 37) for item in goodSecListUnique):
                    raise Exception("Section list {0} is not built correcly".format(goodSecListUnique))
                    # print goodSecListUnique

            if qtr is not None:
                qtrStr = str(qtr)
                goodQtrList = []
                if re.search("[,&]", qtrStr):
                    qtrList = re.split("[,&]", qtrStr)
                    qtrListClean = [item.strip() for item in qtrList]
                    for item in qtrListClean:
                        try:
                            if not re.match("^(N|S)(W|E)$", item):
                                qtrRep = item.split(" ")[0]
                                if re.match("^[NSWE]$", qtrRep):
                                    if re.match("^[NS]$", qtrRep):
                                        goodQtr = [qtrRep + "W", qtrRep + "E"]
                                    elif re.match("^[WE]$", qtrRep):
                                        goodQtr = ["N" + qtrRep, "S" + qtrRep]
                                    goodQtrList.extend(goodQtr)
                                else:
                                    if re.match('^[NSWE]1/2$', qtrRep):
                                        if qtrRep[0] == 'N':
                                            goodQtr = ['NW', 'NE']
                                        elif qtrRep[0] == 'S':
                                            goodQtr = ['SW', 'SE']
                                        elif qtrRep[0] == 'W':
                                            goodQtr = ['NW', 'SW']
                                        else:
                                            goodQtr = ['NE', 'SE']

                                        goodQtrList.extend(goodQtr)
                                    else:
                                        raise Exception("Reconsider for quarter {0}".format(item))
                            else:
                                goodQtrList.append(item)
                        except:
                            continue
                else:
                    if not re.match("^(N|S)(W|E)$", qtrStr):
                        qtrRep = qtrStr.split(" ")[0]
                        if re.match("^[NSWE]$", qtrRep):
                            if re.match("^[NS]$", qtrRep):
                                goodQtr = [qtrRep + "W", qtrRep + "E"]
                            elif re.match("^[WE]$", qtrRep):
                                goodQtr = ["N" + qtrRep, "S" + qtrRep]
                            goodQtrList.extend(goodQtr)
                        else:
                            raise Exception("Reconsider for quarter {0}".format(qtr))
                    else:
                        goodQtrList.append(qtrStr)

                goodQtrListUnique = set(goodQtrList)
                if any(not re.match("^(N|S)(W|E)$", item) for item in goodQtrListUnique):
                    raise Exception("Quarter list {0} is not built correcly".format(goodQtrListUnique))
                    # print goodQtrListUnique

            if lsd is not None:
                try:
                    lsdInt = int(lsd)
                    if lsdInt not in range(0, 17):
                        print("LSD {0} is out of range, and reconsider lsd list".format(lsdInt))
                        lsd = None
                except:
                    lsd = None

            twp = '00' + str(twp)
            rge = '0' + str(rge)
            sec = '0' + str(sec)
            pidList = []

            if sec is None:
                twp = '00' + str(twp)
                rge = '0' + str(rge)
                sec = '0' + str(sec)
                PID = str(mer) + rge[-2:] + twp[-3:]
                pidList.append(PID)
            else:
                for sec in goodSecListUnique:
                    sec = '0' + str(sec)
                    if qtr is None and lsd is None:
                        PID = str(mer) + rge[-2:] + twp[-3:] + sec[-2:]
                        pidList.append(PID)
                    else:
                        if lsd is not None:
                            lsd = '0' + str(lsd)
                            PID = str(mer) + rge[-2:] + twp[-3:] + sec[-2:] + lsd[-2:]
                            pidList.append(PID)
                        else:
                            for qtr in goodQtrListUnique:
                                PID = str(mer) + rge[-2:] + twp[-3:] + sec[-2:] + qtr
                                pidList.append(PID)

            return pidList

        except:
            traceback.print_exc()
            raise

    def getPIDLabel(self, pid_list):
        try:
            pid_label_list = []
            for pid in pid_list:
                if len(pid) in (8, 10):
                    if len(pid) == 10:
                        pid_label = '{0}-{1}-{2}-{3}-W{4}'.format(pid[-2:], pid[-4:-2], pid[3:6], pid[1:3], pid[0])
                    elif len(pid) == 8:
                        pid_label = '{0}-{1}-{2}-W{3}'.format(pid[-2:], pid[3:6], pid[1:3], pid[0])

                    pid_label_list.append(pid_label)

            # print(pid_label_list)

            return pid_label_list
        except:
            traceback.print_exc()
            raise

    def get_latitude_locations(self):
        latitude_locations = GRSJobLocation.objects.filter(jobno=self.jobnumber).values()

        pid_list = []

        for item in latitude_locations:
            try:
                # print(item, type(item))
                LSD = item['lsd'] if len(str(item['lsd']).strip()) > 0 else None
                QTR = item['qtr'] if len(str(item['qtr']).strip()) > 0 else None
                SEC = item['sec'] if len(str(item['sec']).strip()) > 0 else None
                TWP = item['twp'] if len(str(item['twp']).strip()) > 0 else None
                RGE = item['rge'] if len(str(item['rge']).strip()) > 0 else None
                MER = str(item['mer']).strip()[-1] if len(str(item['mer']).strip()) > 0 else None

                if not any(item is None for item in [MER, RGE, TWP, SEC]):
                    pid_list.extend(self.getPID(MER, TWP, RGE, SEC, QTR, LSD))
            except:
                continue

        pid_label_list = self.getPIDLabel(sorted(pid_list))
        pid_label_list_str = ', '.join(pid_label_list)

        return pid_label_list_str

    def get_pm_name(self):
        try:
            pm = EmployeeDetails.objects.get(empcode=self.jobcaptain)
            return '{} {}'.format(pm.firstname, pm.surname)
        except:
            return None

    def get_pm_email(self):
        if self.jobcaptain is not None:
            pm_email = '{}@globalraymac.ca'.format(self.jobcaptain.lower())
        else:
            pm_email = None

        return pm_email

    class Meta:
        managed = False
        db_table = 'vwGRSJobs'
        ordering = ('-jobdate', '-jobnumber')
        verbose_name = 'Latitude Jobs'

    def __unicode__(self):
        return self.jobnumber

    def __repr__(self):
        return self.jobnumber

    def get_fields(self):
        skip_fields = ['jobcaptain']
        value_tuple_list = [(field.verbose_name, field.value_to_string(self))
                            for field in GRSJobInfo._meta.fields
                            if field.name not in skip_fields]
        value_tuple_list.append(('Job Folder', self.latitude_job_folder_full_path()))
        value_tuple_list.append(('Job Locations', self.get_latitude_locations()))
        value_tuple_list.append(('Project Manager', self.get_pm_name()))
        value_tuple_list.append(('PM Email', self.get_pm_email()))

        return value_tuple_list


class GRSJobLocation(models.Model):
    _DATABASE = 'latidatasql'

    jobno = models.CharField(db_column='JobNo', max_length=20, primary_key=True)
    lsd = models.CharField(db_column='LSD', max_length=30, blank=True, null=True)
    qtr = models.CharField(db_column='QTR', max_length=30, blank=True, null=True)
    sec = models.CharField(db_column='SEC', max_length=30, blank=True, null=True)
    twp = models.CharField(db_column='TWP', max_length=30, blank=True, null=True)
    rge = models.CharField(db_column='RGE', max_length=30, blank=True, null=True)
    mer = models.CharField(db_column='MER', max_length=30, blank=True, null=True)
    usage = models.CharField(db_column='Usage', max_length=25, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'vwGRSLegalDescJob'


class EmployeeDetails(models.Model):
    _DATABASE = 'latidatasql'

    empcode = models.CharField(db_column='EmpCode', max_length=50, primary_key=True)
    firstname = models.CharField(db_column='FirstName', max_length=50, blank=True, null=True)
    surname = models.CharField(db_column='Surname', max_length=50, blank=True, null=True)
    defcbcode = models.CharField(db_column='DefCBCode', max_length=20, blank=True, null=True)
    txtdfltworktype = models.CharField(db_column='txtDfltWorkType', max_length=50, blank=True, null=True)
    salary = models.DecimalField(db_column='Salary', max_digits=19, decimal_places=4, blank=True, null=True)
    salaryunits = models.SmallIntegerField(db_column='SalaryUnits', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'vwEmployee'


class Tbljobs(models.Model):
    _DATABASE = 'latidatasql'

    job_number = models.CharField(db_column='Job Number', primary_key=True, max_length=20)
    job_date = models.DateTimeField(db_column='Job Date', blank=True, null=True)
    job_description = models.CharField(db_column='Job Description', max_length=255, blank=True, null=True)
    work_status = models.CharField(db_column='Work Status', max_length=50, blank=True, null=True)
    jobtype = models.CharField(db_column='JobType', max_length=50, blank=True, null=True)
    jobfolder = models.CharField(db_column='JobFolder', max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tblJobs'


class ScriptStatus(models.Model):
    _DATABASE = 'sql01_automation_tracking_db'
    script_id = models.CharField(db_column='Script ID', primary_key=True, max_length=50)
    script_name = models.CharField(db_column='Script Name', unique=True, max_length=50)
    script_path = models.CharField(db_column='Script Path', max_length=255)
    reporting_schedule = models.IntegerField(db_column='Reporting Schedule',
                                             verbose_name='Reporting Schedule (Minutes)')
    latest_report_time = models.DateTimeField(db_column='Latest Report Time', blank=True, null=True)
    next_reporting_time = models.DateTimeField(db_column='Next Reporting Time', blank=True, null=True)
    alert_sent_time = models.DateTimeField(db_column='Alert Sent Time', blank=True, null=True)
    contact_emails = models.TextField(db_column='Contact Emails', max_length=255, blank=True, null=True)
    log_path = models.CharField(db_column='Log Path', max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ScriptsStatus'

    def get_log_path(self, logger_name=None):
        log_file_path = self.log_path

        if log_file_path is not None and os.path.isfile(log_file_path):
            log_file_url = 'file://{}'.format(log_file_path[2:])
            if logger_name is not None:
                log_file_link = format_html('<a href="{0}">{1}</a>'.format(log_file_url, logger_name))
            else:
                log_file_link = format_html('<a href="{0}">{1}</a>'.format(log_file_url, 'Log Link'))

        else:
            log_file_link = None

        return log_file_link

    # def get_log_path(self):
    #     log_file_path = self.log_path
    #
    #     if log_file_path is not None and os.path.isfile(log_file_path):
    #         log_file_url = 'file://{}'.format(log_file_path[2:])
    #         log_file_link = format_html('<a href="{0}">{1}</a>'.format(log_file_url, 'Main Log Link'))
    #     else:
    #         log_file_link = None
    #
    #     return log_file_link

    def save(self, *args, **kwargs):

        super(ScriptStatus, self).save(*args, **kwargs)


class FortisJobExtents(models.Model):
    _DATABASE = 'fortis'

    object_id = models.IntegerField(db_column='OBJECTID', primary_key=True)
    job_no = models.CharField(db_column='Job_Number', max_length=8)
    site_id = models.IntegerField(db_column='SiteID')

    class Meta:
        managed = False
        db_table = 'vi_FortisFieldPageExtents'

    @classmethod
    def get_sites(cls, job_no):
        return sorted(list(set([item.site_id for item in cls.objects.filter(job_no=job_no)])))


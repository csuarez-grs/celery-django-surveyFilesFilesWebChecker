import glob
import re

import arcpy
import project_settings as fortis
import Master_Functions as ma


def find_numbers(obj):
    profiles_count = None
    points_count = None
    structures_count = None
    profiles_meters = None
    try:
        site_db = getattr(obj, 'site_data_db', None)
        if not site_db:
            site_folder = getattr(obj, 'site_folder', None)
            job_no = getattr(obj, 'job_no', None)
            site_no = getattr(obj, 'site_no', None)
            if site_folder:
                site_db = r'{}\{}_site_{}.gdb'.format(site_folder, job_no, site_no)

        if site_db and arcpy.Exists(site_db):
            survey_pts = r'{}\SurveyPts'.format(site_db)
            profile_fc = r'{}\Profile'.format(site_db)
            if arcpy.Exists(profile_fc):
                profiles_count = ma.countRecords(profile_fc)
                profiles_meters = 0
                for row in arcpy.da.SearchCursor(profile_fc, ['SHAPE@']):
                    row_length = row[0].getLength('PLANAR', 'METERS')
                    profiles_meters += row_length
                profiles_meters = int(round(profiles_meters))

            if arcpy.Exists(survey_pts):
                points_count = ma.countRecords(survey_pts)
                structures_count = len([row[0] for row in
                                        arcpy.da.SearchCursor(survey_pts,
                                                              [fortis.point_profile_no_field],
                                                              where_clause='{} is not null and {} is not null'
                                                              .format(fortis.point_profile_no_field,
                                                                      fortis.profile_order_no_field))
                                        ])
                if profiles_count is None:
                    profiles_count = len(set([row[0] for row in
                                              arcpy.da.SearchCursor(survey_pts,
                                                                    [fortis.point_profile_no_field],
                                                                    where_clause='{} is not null'
                                                                    .format(fortis.point_profile_no_field))
                                              ]))
    except Exception as e:
        print('Errors: {}'.format(e))

    print('Getting: {} {} {} {} meters'.format(profiles_count, points_count, structures_count, profiles_meters))

    return profiles_count, points_count, structures_count, profiles_meters

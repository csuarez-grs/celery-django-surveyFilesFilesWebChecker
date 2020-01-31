import django_tables2 as tables

from .models import SurveyFileAutomation


class StatusUpdateLinkColumn(tables.LinkColumn):
    def render(self, value, record, bound_column):
        if record.uuid is None or record.folder_name == 'Tracking':
            return '---'
        return super(StatusUpdateLinkColumn, self).render(value, record, bound_column)


class SurveyFileAutomationTable(tables.Table):
    # target_url = tables.Column(accessor='get_target_url', verbose_name='Target URL', orderable=False)
    log_link = tables.Column(accessor='get_log_link', verbose_name='Log Link', orderable=False)
    # document_link = tables.Column(accessor='get_survey_file_link', verbose_name='Document', orderable=False)
    field_folder_link = tables.Column(accessor='get_field_folder_link', verbose_name='Target Field Folder', orderable=False)
    # time_ago = tables.Column(accessor='get_time_ago', verbose_name='Time to Now', orderable=False)
    # transferred_date = tables.Column(accessor='get_transferred_date', verbose_name='Transferred Date',
    #                                  orderable=False)
    # update_details = StatusUpdateLinkColumn('ftp_item_edit', text='Edit', args=[A('pk')], orderable=False)
    exp_links = tables.Column(accessor='get_exp_links', verbose_name='EXP Links', orderable=False)
    ald_csv_links = tables.Column(accessor='get_ald_csv_links', verbose_name='ALD CSV Links', orderable=False)
    wgs_84_csv_link = tables.Column(accessor='get_wgs_84_csv_link', verbose_name='WGS 84 CSV Link', orderable=False)
    kmz_link = tables.Column(accessor='get_kmz_link', verbose_name='KMZ Link', orderable=False)

    class Meta:
        model = SurveyFileAutomation
        fields = (
            'uploaded_time',
            'job_no',
            'site_no',
            # 'time_ago',
            'uploader',
            'document',
            'field_folder_link',
            'log_link',
            'project_manager',
            'qc_time',
            'qc_passed',
            'jxl_errors',
            'overwriting',
            'automation_started',
            'automation_ended',
            'automation_status',
            'done_with_automation',
            'exp_links',
            'ald_csv_links',
            'wgs_84_csv_link',
            'kmz_link',
            'errors'
            # 'update_details'
        )
        # template_name = 'django_tables2/semantic.html'
        template_name = 'django_tables2/bootstrap.html'

        # per_page = 20

        # attrs = {
        #     'id': '',
        # "class": "table-striped table-bordered",
        # 'class': 'paleblue',
        #  'width': '90%',
        # 'th': {
        #     'style': 'text-align: center;'
        # },
        # 'td': {
        #     # 'data-length': lambda value: len(value) * 1.5,
        #     'style': 'text-align: left;'
        #
        # },
        # }

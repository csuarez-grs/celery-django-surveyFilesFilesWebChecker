from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SurveyFilesWebChecker.settings')
app = Celery('SurveyFilesWebChecker')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.conf.update(
    CELERY_RESULT_PERSISTENT=True,
    CELERY_TASK_RESULT_EXPIRES=None,
    CELERY_IGNORE_RESULT=False,
    CELERY_TRACK_STARTED=True,
)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

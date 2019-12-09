activate_this = r'\\grs.com\DFS\GIS\GIS_Main\20_Development\Django\SurveyFilesWebChecker\checker-env\Scripts\activate_this.py'
# execfile(activate_this, dict(__file__=activate_this))
exec(open(activate_this).read(),dict(__file__=activate_this))

import os
import sys
import site

# Add the site-packages of the chosen virtualenv to work with
site.addsitedir(r'\\grs.com\DFS\GIS\GIS_Main\20_Development\Django\SurveyFilesWebChecker\checker-env\Lib\site-packages')

# Add the app's directory to the PYTHONPATH
sys.path.append(r'\\grs.com\DFS\GIS\GIS_Main\20_Development\Django\SurveyFilesWebChecker')
sys.path.append(r'\\grs.com\DFS\GIS\GIS_Main\20_Development\Django\SurveyFilesWebChecker\SurveyFilesWebChecker')

os.environ['DJANGO_SETTINGS_MODULE'] = 'SurveyFilesWebChecker.settings'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SurveyFilesWebChecker.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
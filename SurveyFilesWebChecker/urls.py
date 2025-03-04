"""SurveyFilesWebChecker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/login/$', auth_views.LoginView.as_view(), name='login'),
    # url(r'^accounts/signup/$', views.signup, name='signup'),
    url(r'^accounts/logout/$', auth_views.LogoutView.as_view(), name='logout'),
    # url(r'^accounts/', include('django.contrib.auth.urls')),
    url('surveyfiles/', include('surveyfiles.urls', namespace='surveyfiles')),
    url(r'api-auth/', include('rest_framework.urls')),
    url(r'rest-auth/', include('rest_auth.urls')),
    url('surveyfiles/api/', include('surveyfiles.api.urls'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

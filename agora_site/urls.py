# Copyright (C) 2012 Eduardo Robles Elvira <edulix AT wadobo DOT com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from djsgettext.views import I18n

from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = patterns('',
    (r'^accounts/', include('agora_site.accounts.urls')),

    (r'^comments/', include('django.contrib.comments.urls')),

    url(r'^js-gettext/$', I18n.as_view(), name="jsgettext"),

    (r'', include('social_auth.urls')),

    (r'', include('agora_site.agora_core.urls')),

    url(r'^captcha/', include('captcha.urls')),
)

if 'django.contrib.admin' in settings.INSTALLED_APPS and settings.DEBUG:
    from django.contrib import admin
    admin.autodiscover()
    urlpatterns += patterns('',
        (r'^admin/', include(admin.site.urls))
    )

urlpatterns += staticfiles_urlpatterns()

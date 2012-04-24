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

from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy  as _

from endless_pagination.views import AjaxListView

from agora_site.agora_core.views import (HomeView, AgoraView, CreateAgoraView,
    AgoraBiographyView, AgoraMembersView, CreateElectionView, ElectionView,
    SetLanguageView)
from agora_site.misc.utils import RequestCreateView

urlpatterns = patterns('',
    url(r'^$', HomeView.as_view(), name='home'),

    url(r'^misc/set-language/(?P<language>[\-\w]+)$', SetLanguageView.as_view(), name="set-language"),

    url(r'^agora/new$', CreateAgoraView.as_view(), name='agora-new'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)$',
        AgoraView.as_view(), name='agora-view'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/biography$',
        AgoraBiographyView.as_view(), name='agora-bio'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/biography/edit$',
        # TODO: create this view!
        AgoraBiographyView.as_view(), name='agora-bio-edit'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/members$',
        AgoraMembersView.as_view(), name='agora-members'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/new',
        CreateElectionView.as_view(), name='election-new'),

    url(r'^(?P<username>[\.\w]+)/(?P<agoraname>[\-\.\w]+)/election/(?P<electionname>[\-\.\w]+)/view$',
        ElectionView.as_view(), name='election-view'),

    url(r'^userlist$', AjaxListView.as_view(
        queryset=User.objects.all(),
        template_name='agora_core/user_list.html',
        page_template='agora_core/user_list_page.html'),
        name="user-list"
    ),
)

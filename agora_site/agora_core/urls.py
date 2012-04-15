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
from endless_pagination.views import AjaxListView
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView
from django.contrib.auth.models import User

from agora_site.agora_core.forms import CreateAgoraForm
from django.utils.translation import ugettext_lazy  as _

urlpatterns = patterns('',
    url(r'^agora/new$', login_required(
        CreateView.as_view(
            template_name='agora_core/create_agora_form.html',
            form_class=CreateAgoraForm,
            success_url = '')), #reverse('agora-view')
        name='agora-new'
    ),
    url(r'^user/list$', AjaxListView.as_view(
        queryset=User.objects.all(),
        template_name='agora_core/user_list.html',
        page_template='agora_core/user_list_page.html'),
        name="user-list"
    ),
)

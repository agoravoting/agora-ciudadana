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

from django.conf.urls import patterns, url, include
from django.views.generic import TemplateView
from django.views.generic import ListView
from django import http
from django.utils import simplejson as json
from django.contrib.auth.models import User
import reversion

class TestView(TemplateView):
    template_name = 'base.html'

    def render_to_response(self, context):

        #user = User.objects.all()[0]
        #print reversion.get_unique_for_object(user)
        #with reversion.create_revision():
            #user.last_name = user.last_name + ", aa"
            #user.save()
            #reversion.set_user(user)
            #reversion.set_comment("Comment text...")

        #print reversion.get_unique_for_object(user)

        return super(TestView, self).render_to_response(context)

    #@method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(TestView, self).dispatch(*args, **kwargs)
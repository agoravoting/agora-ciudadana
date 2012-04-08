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
from django.conf import settings
from django.views.generic import TemplateView
from django.views.generic import ListView
from django import http
from django.utils import simplejson as json
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm,UserCreationForm
from django.utils.translation import ugettext as _
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.contrib import messages

class AuthView(TemplateView):
    '''
    View with multiple purposes: both login and register forms are rendered
    and processed in this view
    '''
    template_name = 'agora-core/auth.html'

    def post(self, request, action=None):
        context = self.get_context_data()

        if self.request.POST.get('type', '') == 'login':
            context['login_form'] = form = AuthenticationForm(data=self.request.POST)
            context['register_form'] = UserCreationForm()
            context['action'] = 'login'

            if form.is_valid():
                user = form.user_cache
                login(self.request, user)
                return redirect('/')
        else:
            context['register_form'] = form = UserCreationForm(self.request.POST)
            context['login_form'] = AuthenticationForm()
            context['action'] = 'register'

            if form.is_valid():
                new_user = form.save()
                messages.add_message(self.request, messages.SUCCESS,
                    _('Welcome to %s! We sent you an email, please check it.')\
                        % settings.SITE_NAME)
                login(self.request, new_user)
                return redirect('/')

        return super(AuthView, self).render_to_response(context)

    def get(self, request, action=None):
        context = self.get_context_data()
        context['login_form'] = AuthenticationForm()
        context['register_form'] = UserCreationForm()
        context['action'] = action

        return super(AuthView, self).render_to_response(context)

    #@method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AuthView, self).dispatch(*args, **kwargs)

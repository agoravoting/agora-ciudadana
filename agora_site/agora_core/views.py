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
from django.contrib.auth.forms import AuthenticationForm,UserCreationForm
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect

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
        
# 

class Entry(TemplateView):
    template_name = 'agora-core/entry.html'
    
    
    def post(self, request):
        import ipdb; ipdb.set_trace()
        
        context = self.get_context_data()
        
        
        
        if self.request.POST.get('type') == 'login':    
            context['login_form'] = AuthenticationForm(self.request.POST)
            context['register_form'] = UserCreationForm()        
            username = self.request.POST['username']
            password = self.request.POST['password']
            user = authenticate(username=username, password=password)
            context['login_form'].is_valid()
                    
            if user is not None and not user.is_anonymous():
                if user.is_active:
                    login(self.request, user)
                    return redirect('/')
                else:
                    pass
            else:
                pass
        else:
            context['register_form'] = UserCreationForm(self.request.POST)
            context['login_form'] = AuthenticationForm()
            pass
                
        return super(Entry, self).render_to_response(context)
                
                
    def get(self, request):
        context = self.get_context_data()
        context['login_form'] = AuthenticationForm()
        context['register_form'] = UserCreationForm()
        
        return super(Entry, self).render_to_response(context)
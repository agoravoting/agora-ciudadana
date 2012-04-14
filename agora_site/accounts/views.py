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
from django.core.urlresolvers import reverse
from django import http
from django.utils import simplejson as json
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.contrib import messages

class SignUpCompleteView(TemplateView):
    def get(self, request, username):
        messages.add_message(request, messages.SUCCESS, _('Registration ' +
            'successful! We have sent the activation link to your email ' +
            'address, look it up.'))
        return redirect('/')

class PasswordResetDoneView(TemplateView):
    def get(self, request):
        messages.add_message(request, messages.SUCCESS, _('An e-mail has been '
            + 'send to you which explains how to reset your password'))
        return redirect('/')


class PasswordResetCompleteView(TemplateView):
    def get(self, request):
        messages.add_message(request, messages.SUCCESS, _('Your password has '
            + 'been reset, you can now <a href="%(url)s">login</a> with your '
            + 'new password') % dict(url=reverse('userena_signin')))
        return redirect('/')


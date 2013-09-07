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

from django import http
from django.conf import settings
from django.conf.urls import patterns, url, include
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.utils.translation import ugettext as _
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.generic import ListView
from django.views.generic.edit import FormView

from userena.models import UserenaSignup
from userena.managers import SHA1_RE
from .forms import RegisterCompleteInviteForm, RegisterCompleteFNMTForm

from userena import views as userena_views
from agora_site.misc.utils import rest

class SignUpCompleteView(TemplateView):
    def get(self, request, username):
        messages.add_message(request, settings.SUCCESS_MODAL, _('Registration '
            'successful! We have sent the activation link to your email '
            'address, look it up. If you don\'t receive the email, please try to locate it in the SPAM folder.'))
        return redirect('/')

class PasswordResetDoneView(TemplateView):
    def get(self, request):
        messages.add_message(request, settings.SUCCESS_MODAL, _('An e-mail has been '
            'sent to you which explains how to reset your password'))
        return redirect('/')

class PasswordResetCompleteView(TemplateView):
    def get(self, request):
        messages.add_message(request, settings.SUCCESS_MODAL, _('Your password has '
            'been reset, you can now <a href="%(url)s">log in</a> with your '
            'new password') % dict(url=reverse('userena_signin')))
        return redirect('/')

class RegisterCompleteInviteView(FormView):
    template_name = 'accounts/complete_registration_invite_form.html'
    form_class = RegisterCompleteInviteForm
    success_url = '/'

    def get_form_kwargs(self):
        kwargs = super(RegisterCompleteInviteView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        kwargs.update({'userena_signup_obj': self.userena_signup_obj})
        return kwargs

    def form_valid(self, form):
        form.save()
        return redirect('/')

    def dispatch(self, request, *args, **kwargs):
        self.activation_key = kwargs['activation_key']
        if SHA1_RE.search(self.activation_key):
            try:
                self.userena_signup_obj = UserenaSignup.objects.get(activation_key=self.activation_key)
            except:
                messages.add_message(request, messages.ERROR, _('Invalid activation link.'))
                return redirect('/')
            if self.userena_signup_obj.activation_key_expired():
                messages.add_message(request, messages.ERROR, _('Invalid activation link.'))
                return redirect('/')
        else:
            messages.add_message(request, messages.ERROR, _('Invalid activation link.'))
            return redirect('/')
        return super(RegisterCompleteInviteView, self).dispatch(request, *args, **kwargs)


class AutoJoinActivateView(TemplateView):
    def get(self, request, username, activation_key, auto_join_activation_key, **kwargs):        
        if(auto_join_activation_key == md5(activation_key + settings.AUTO_JOIN_SECRET)):
            # auto join logic
            user = User.objects.filter(name = username)
            profile = new_user.get_profile()
            for agora_name in settings.AGORA_REGISTER_AUTO_JOIN:
                agora = Agora.objects.filter(name = agora_name)
                if agora.Agora.MEMBERSHIP_TYPE[0][0]:
                    profile.add_to_agora(agora_name=agora_name, request=self.request)                    
                else:
                    # request membership here
                    resp = rest('/agora/%s/action/' % agora.id, 
                        data={'action': 'add_membership',
                        'username': user.username,
                        'welcome_message': _("Welcome to this agora")},
                        method="POST",
                        request=request)                    
            userena_views.activate(request, username, activation_key, kwargs['template_name'], kwargs['success_url'])
        else:            
            userena_views.activate(activation_key='bogus')                      
        
class RegisterCompleteFNMTView(FormView):
    template_name = 'accounts/complete_registration_fnmt_form.html'
    form_class = RegisterCompleteFNMTForm
    success_url = '/'

    def get_form_kwargs(self):
        kwargs = super(RegisterCompleteFNMTView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        kwargs.update({'userena_signup_obj': self.userena_signup_obj})
        return kwargs

    def form_valid(self, form):
        form.save()
        return redirect(settings.LOGIN_REDIRECT_URL)

    def dispatch(self, request, *args, **kwargs):
        self.activation_key = kwargs['activation_key']
        if SHA1_RE.search(self.activation_key):
            try:
                self.userena_signup_obj = UserenaSignup.objects.get(activation_key=self.activation_key)
            except:
                messages.add_message(request, messages.ERROR, _('Invalid activation link.'))
                return redirect('/')
            if self.userena_signup_obj.activation_key_expired():
                messages.add_message(request, messages.ERROR, _('Invalid activation link.'))
                return redirect('/')
        else:
            messages.add_message(request, messages.ERROR, _('Invalid activation link.'))
            return redirect('/')
        return super(RegisterCompleteFNMTView, self).dispatch(request, *args, **kwargs)

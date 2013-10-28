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

import hashlib
import json

from django import http
from django.conf import settings
from django.conf.urls import patterns, url, include
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.utils.translation import ugettext as _
from django.utils import translation, timezone
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.views.generic.edit import FormView
from guardian.shortcuts import assign, remove_perm

from userena import views as userena_views
from userena import settings as userena_settings
from userena.models import UserenaSignup
from userena.managers import SHA1_RE

from agora_site.misc.utils import rest
from agora_site.agora_core.models.agora import Agora
from agora_site.agora_core.models.castvote import CastVote
from .forms import RegisterCompleteInviteForm, RegisterCompleteFNMTForm, SignupAndVoteForm

class SignUpCompleteView(TemplateView):
    def get(self, request, username):
        messages.add_message(request, settings.SUCCESS_MODAL, _('Registration '
            'successful! We have sent the activation link to your email '
            'address, look it up. If you don\'t receive the email, please try to locate it in the SPAM folder. <strong>You will only be able to vote when we review and verify your scanned ID.</strong>'))
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

class SignupAndVoteView(FormView):
    template_name = 'accounts/empty.html'
    form_class = SignupAndVoteForm

    def get_form_kwargs(self):
        kwargs = super(SignupAndVoteView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        return http.HttpResponse(json.dumps(form.save()))

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
    def get(self, request, username, activation_key, **kwargs):
        if not settings.AGORA_REGISTER_AUTO_JOIN:
            messages.add_message(request, messages.ERROR, _('Invalid activation link.'))
            return redirect('/')

        try:
            userena = UserenaSignup.objects.get(user__username=username)
        except:
            return userena_views.activate(request, username=username, activation_key='bogus')

        hashed_key = hashlib.md5(userena.activation_key + settings.AGORA_API_AUTO_ACTIVATION_SECRET).hexdigest()
        if hashed_key != activation_key and activation_key != userena.activation_key:
            return userena_views.activate(request, username=username, activation_key='bogus')

        user = User.objects.get(username=username)
        profile = user.get_profile()
        requested_membership = False
        for agora_name in settings.AGORA_REGISTER_AUTO_JOIN:
            username2, agoraname = agora_name.split("/")
            agora = get_object_or_404(Agora, name=agoraname,
                creator__username=username2)
            if agora.membership_policy == Agora.MEMBERSHIP_TYPE[0][0] or\
                    activation_key == userena.activation_key:
                profile.add_to_agora(agora_name=agora_name, request=self.request)
            else:
                # request membership here
                assign('requested_membership', user, agora)
                requested_membership = True

        if requested_membership:
            messages.add_message(request, settings.SUCCESS_MODAL, _("Your account has been activated, but <strong>in order to vote have to verify your ID</strong> scanning attachment you sent us. Stay tuned <strong>attentive to your email</strong>, soon verify your identity and you will get an email saying you've entered the agora <strong>%s</strong> - You can then vote on the bill and make history with us.") % settings.AGORA_REGISTER_AUTO_JOIN[0])
        return userena_views.activate(request, username, userena.activation_key, kwargs['template_name'], kwargs['success_url'])



class AutoLoginTokenView(TemplateView):
    def get(self, request, username, token, **kwargs):
        user = get_object_or_404(User, username=username)
        if not default_token_generator.check_token(user, token):
            messages.add_message(request, messages.ERROR, _('Invalid login link.'))
            return redirect('/')

        profile = user.get_profile()
        for agora_name in settings.AGORA_REGISTER_AUTO_JOIN:
            profile.add_to_agora(agora_name=agora_name, request=request)

        setattr(user, 'backend', 'django.contrib.auth.backends.ModelBackend')
        login(request, user)
        request.session.set_expiry(userena_settings.USERENA_REMEMBER_ME_DAYS[1] * 86400)
        return redirect('/')


class ConfirmVoteTokenView(TemplateView):
    def get(self, request, username, token, **kwargs):
        user = get_object_or_404(User, username=username)
        if not default_token_generator.check_token(user, token):
            messages.add_message(request, messages.ERROR, _('Invalid confirmation link.'))
            return redirect('/')

        if not user.is_active:
            user.is_active = True
            user.save()
            for agora_name in settings.AGORA_REGISTER_AUTO_JOIN:
                username2, agoraname = agora_name.split("/")
                agora = get_object_or_404(Agora, name=agoraname,
                    creator__username=username2)
                if agora.membership_policy == Agora.MEMBERSHIP_TYPE[0][0]:
                    profile.add_to_agora(agora_name=agora_name, request=request)
                else:
                    # request membership here
                    assign('requested_membership', user, agora)
        setattr(user, 'backend', 'django.contrib.auth.backends.ModelBackend')

        profile = user.get_profile()
        if not isinstance(profile.extra, dict) or\
            'pending_ballot_id' not in profile.extra:
            messages.add_message(request, messages.ERROR, _('Invalid confirmation link.'))
            return redirect('/')
        vote = get_object_or_404(CastVote, id=profile.extra['pending_ballot_id'])
        status_str = 'pending_ballot_status_%d' % vote.id

        login(request, user)
        request.session.set_expiry(userena_settings.USERENA_REMEMBER_ME_DAYS[1] * 86400)

        if vote.election.has_perms('vote_counts', user):
            # invalidate older votes from the same voter to the same election
            old_votes = vote.election.cast_votes.filter(is_direct=True,
                invalidated_at_date=None, voter=user)
            for old_vote in old_votes:
                if old_vote.id == vote.id:
                    continue
                old_vote.invalidated_at_date = timezone.now()
                old_vote.is_counted = False
                old_vote.save()
            vote.is_counted = True
            vote.save()

            del profile.extra['pending_ballot_id']
            if status_str in profile.extra:
                del profile.extra[status_str]
            profile.save()
            messages.add_message(request, settings.SUCCESS_MODAL, _("Your ballot has been confirmed and was successfully cast"))
            return redirect('/')

        profile.extra[status_str] = 'confirmed'
        profile.save()

        messages.add_message(request, settings.SUCCESS_MODAL, _("Your email address has been confirmed, but your ballot will not be confirmed until we manually verify your identity. We'll try to do it as soon as possible, and we'll keep you posted."))
        return redirect('/')


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

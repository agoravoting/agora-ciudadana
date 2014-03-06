# Copyright (C) 2013 Eduardo Robles Elvira <edulix AT wadobo DOT com>
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


from agora_site.agora_core.models import Agora, Election, CastVote
from agora_site.agora_core.tasks.election import (start_election, end_election)
from agora_site.agora_core.models.voting_systems.base import get_voting_system_by_id
from agora_site.misc.utils import *

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden, Layout, Fieldset
from actstream.models import Action
from actstream.signals import action as actstream_action
from actstream.actions import follow, unfollow, is_following
from userena.models import UserenaSignup
from userena import settings as userena_settings

from django import forms as django_forms
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.comments.forms import CommentSecurityForm
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils import simplejson as json
from django.utils import translation, timezone
from django.contrib.sites.models import Site
from django.db import transaction

import uuid
import datetime
import requests
import random
import re

class VoteForm(django_forms.ModelForm):
    '''
    Given an election, creates a form that lets the user choose the options
    he want to vote
    '''
    is_vote_secret = django_forms.BooleanField(required=False)

    issue_date = django_forms.CharField(required=False, max_length=120)

    unique_randomness = django_forms.CharField(required=False, max_length=120)

    check_token = False

    def __init__(self, request, election, *args, **kwargs):
        super(VoteForm, self).__init__(*args, **kwargs)
        self.election = election
        self.request = request

        i = 0
        for question in election.questions:
            voting_system = get_voting_system_by_id(question['tally_type'])
            field = voting_system.get_question_field(election, question)
            self.fields.insert(0, 'question%d' % i, field)
            i += 1

    def clean_token(self):
        '''
        Reimplemented in subclass where check_token is True
        '''
        pass

    def notify_counterpart(self):
        '''
        Reimplemented in subclass where check_token is True
        '''
        pass

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        election = get_object_or_404(Election, pk=kwargs["electionid"])
        return dict(request=request, election=election, data=data)

    def clean(self):
        cleaned_data = super(VoteForm, self).clean()

        if self.check_token:
            self.clean_token()

        if not 'is_vote_secret' in self.data:
            raise django_forms.ValidationError("is_vote_secret is a required field.")

        cleaned_data['is_vote_secret'] = bool(self.data['is_vote_secret'])

        if not self.election.ballot_is_open():
            raise django_forms.ValidationError("Sorry, you cannot vote in this election.")

        if not self.check_token and cleaned_data['is_vote_secret'] and\
            not self.election.has_perms('vote_counts', self.request.user):
            raise django_forms.ValidationError("Sorry, you cannot vote secretly in "
                "this election because you can only act as a delegate.")

        if cleaned_data['is_vote_secret'] and not self.election.is_vote_secret:
            raise django_forms.ValidationError("Sorry, this election allows only "
                "public votes.")

        return cleaned_data

    def bundle_obj(self, vote, request):
        from agora_site.agora_core.resources.castvote import CastVoteResource
        cvr = CastVoteResource()
        bundle = cvr.build_bundle(obj=vote, request=self.request)
        bundle = cvr.full_dehydrate(bundle)
        return bundle

    def save(self, *args, **kwargs):
        # invalidate older votes from the same voter to the same election
        if not self.check_token:
            old_votes = self.election.cast_votes.filter(is_direct=True,
                invalidated_at_date=None, voter=self.request.user)
            for old_vote in old_votes:
                old_vote.invalidated_at_date = timezone.now()
                old_vote.is_counted = False
                old_vote.save()
        vote = super(VoteForm, self).save(commit=False)

        if not self.check_token:
            voter = self.request.user
            voter_username = self.request.user.username
        else:
            voter = self.election.agora.admins.all()[0]

        # generate vote
        if self.election.is_secure() and self.cleaned_data['is_vote_secret']:
            data = {
                "a": "encrypted-vote-v1",
                "proofs": [],
                "choices": [],
                "issue_date": self.cleaned_data["issue_date"],
                "election_hash": {"a": "hash/sha256/value", "value": self.election.hash},
                "election_uuid": self.election.uuid
            }
            i = 0
            for question in self.election.questions:
                q_answer =self.data['question%d' % i]
                data["proofs"].append(dict(
                    commitment=q_answer['commitment'],
                    response=q_answer['response'],
                    challenge=q_answer['challenge']
                ))
                data["choices"].append(dict(
                    alpha=q_answer['alpha'],
                    beta=q_answer['beta']
                ))
                i += 1
        else:
            data = {
                "a": "plaintext-vote-v1",
                "answers": [],
                "unique_randomness": self.cleaned_data["unique_randomness"],
                "election_hash": {"a": "hash/sha256/value", "value": self.election.hash},
                "election_uuid": self.election.uuid
            }
            i = 0
            for question in self.election.questions:
                data["answers"] += [self.cleaned_data['question%d' % i]]
                i += 1

        # fill the vote
        vote.voter = voter
        vote.election = self.election
        vote.is_counted = self.election.has_perms('vote_counts', voter)
        vote.is_direct = True

        # stablish if the vote is secret
        if self.election.is_vote_secret() and self.cleaned_data['is_vote_secret']:
            vote.is_public = False
            vote.reason = None
        else:
            vote.reason = clean_html(self.cleaned_data['reason'])
            vote.is_public = True

        # assign data, create hash etc
        vote.data = data
        vote.casted_at_date = timezone.now()
        vote.create_hash()

        # create action
        if not settings.ANONYMIZE_USERS:
            actstream_action.send(self.request.user, verb='voted', action_object=self.election,
                target=self.election.agora,
                geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

            vote.action_id = Action.objects.filter(actor_object_id=self.request.user.id,
                verb='voted', action_object_object_id=self.election.id,
                target_object_id=self.election.agora.id).order_by('-timestamp').all()[0].id

        # before saving the vote, send the notification that the user voted to
        # agora-election if check_token is activated
        if self.check_token:
            self.notify_counterpart()

        vote.save()

        if not self.check_token:
            # send email
            context = get_base_email_context(self.request)
            context.update(dict(
                to=self.request.user,
                election=self.election,
                vote_hash=vote.hash,
                election_url=self.election.get_link(),
                agora_url=self.election.get_link(),
            ))

            if self.request.user.has_perms('receive_email_updates'):
                translation.activate(self.request.user.get_profile().lang_code)
                email = EmailMultiAlternatives(
                    subject=_('Vote casted for election %s') % self.election.pretty_name,
                    body=render_to_string('agora_core/emails/vote_casted.txt',
                        context),
                    to=[self.request.user.email])

                email.attach_alternative(
                    render_to_string('agora_core/emails/vote_casted.html',
                        context), "text/html")
                email.send()
                translation.deactivate()

            if not is_following(self.request.user, self.election):
                follow(self.request.user, self.election, actor_only=False, request=self.request)

        return vote

    class Meta:
        model = CastVote
        fields = ('reason',)


class TokenVoteForm(VoteForm):
    is_vote_secret = django_forms.BooleanField(required=False)

    issue_date = django_forms.CharField(required=False, max_length=120)

    unique_randomness = django_forms.CharField(required=False, max_length=120)

    message = django_forms.CharField(required=False, max_length=200)

    sha1_hmac = django_forms.CharField(required=False, max_length=120)

    check_token = True

    def clean_token(self):
        '''
        Check message authentication and validation
        '''
        message = self.data['message']
        sha1_hmac = self.data['sha1_hmac']
        if not settings.AGORA_USE_AUTH_TOKEN_VALIDATION:
            raise django_forms.ValidationError("Sorry, agora auth token validation is not active.")

        if not isinstance(message, basestring):
            raise django_forms.ValidationError("Sorry, you didn't provide a validation message.")
        if not isinstance(sha1_hmac, basestring):
            raise django_forms.ValidationError("Sorry, you didn't provide a sha1_hmac.")

        if not re.match("^\d+#[^#]+$", message):
            raise django_forms.ValidationError("Invalid validation message.")

        key = settings.AGORA_API_AUTO_ACTIVATION_SECRET
        hmac = salted_hmac(key, message, "").hexdigest()

        timestamp = int(message.split("#")[0])
        now = datetime.datetime.utcnow()
        d = datetime.datetime.fromtimestamp(timestamp)
        max_secs = settings.AGORA_TOKEN_VALIDATION_EXPIRE_SECS

        if now - d > datetime.timedelta(seconds=max_secs):
            raise django_forms.ValidationError("Too old validation message.")

        if not constant_time_compare(sha1_hmac, hmac):
            raise django_forms.ValidationError("Invalid sha1_hmac.")

    def notify_counterpart(self):
        '''
        Reimplemented in subclass where check_token is True
        '''
        key = settings.AGORA_API_AUTO_ACTIVATION_SECRET
        message = self.data['message'].split("#")[1] # this is the "voter id"
        payload = dict(
            identifier=message, # this is the "voter id"
            sha1_hmac=salted_hmac(key, message, "").hexdigest()
        )
        r = requests.post(settings.AGORA_TOKEN_NOTIFY_URL,
            data=json.dumps(payload), verify=False,
            auth=settings.AGORA_TOKEN_NOTIFY_URL_AUTH)
        if r.status_code != 200:
            print("r.text = " + r.text)
            raise Exception("Sorry, we couldn't invalidate vote token")


class LoginAndVoteForm(django_forms.ModelForm):
    '''
    Given an election, creates a form that lets the user choose the options
    he want to vote
    '''
    is_vote_secret = django_forms.BooleanField(required=False)
    user_id = django_forms.CharField(required=True, max_length=120)
    password = django_forms.CharField(required=True, max_length=20)
    issue_date = django_forms.CharField(required=False, max_length=120)

    bad_password = False
    is_active = True
    user = None

    check_user = True

    def __init__(self, request, election, *args, **kwargs):
        super(LoginAndVoteForm, self).__init__(*args, **kwargs)
        self.election = election
        self.request = request

        i = 0
        for question in election.questions:
            voting_system = get_voting_system_by_id(question['tally_type'])
            field = voting_system.get_question_field(election, question)
            self.fields.insert(0, 'question%d' % i, field)
            i += 1

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        election = get_object_or_404(Election, pk=kwargs["electionid"])
        return dict(request=request, election=election, data=data)

    def clean(self):
        cleaned_data = super(LoginAndVoteForm, self).clean()

        if not self.election.ballot_is_open():
            raise django_forms.ValidationError("Sorry, you cannot vote in this election.")

        if cleaned_data['is_vote_secret'] and not self.election.is_vote_secret:
            raise django_forms.ValidationError("Sorry, this election allows only "
                "public votes.")

        if not 'is_vote_secret' in self.data:
            raise django_forms.ValidationError("is_vote_secret is a required field.")

        cleaned_data['is_vote_secret'] = bool(self.data['is_vote_secret'])

        if self.check_user and 'user_id' not in cleaned_data:
            raise django_forms.ValidationError("user_id is a required field.")
        if 'password' not in cleaned_data:
            raise django_forms.ValidationError("password is a required field.")

        # check user
        if self.check_user:
            user_q = User.objects.filter(username=cleaned_data['user_id'])
            if user_q.count() > 0:
                self.user = user_q[0]
            else:
                user_q = User.objects.filter(email=cleaned_data['user_id'])
                if user_q.count() == 0:
                    raise django_forms.ValidationError("User not found.")
                self.user = user_q[0]

            self.is_active = self.user.is_active

            # now we have an user, try to login
            assert self.user
            try:
                user = authenticate(identification=self.user.username, password=cleaned_data['password'])
                if self.user.is_active:
                    login(self.request, user)
            except Exception, e:
                self.bad_password = True

        return cleaned_data

    def bundle_obj(self, vote, request):
        from agora_site.agora_core.resources.castvote import CastVoteResource
        cvr = CastVoteResource()
        bundle = cvr.build_bundle(obj=vote, request=self.request)
        bundle = cvr.full_dehydrate(bundle)
        return bundle

    def save(self, *args, **kwargs):
        if not self.bad_password and self.is_active:
            # invalidate older votes from the same voter to the same election
            old_votes = self.election.cast_votes.filter(is_direct=True,
                invalidated_at_date=None, voter=self.user)
            for old_vote in old_votes:
                old_vote.invalidated_at_date = timezone.now()
                old_vote.is_counted = False
                old_vote.save()

        vote = super(LoginAndVoteForm, self).save(commit=False)
        vote.is_counted = not self.bad_password and self.is_active and self.election.has_perms('vote_counts', self.user)

        # generate vote
        # generate vote
        if self.election.is_secure() and self.cleaned_data['is_vote_secret']:
            data = {
                "a": "encrypted-vote-v1",
                "proofs": [],
                "choices": [],
                "voter_username": self.request.user.username,
                "issue_date": self.cleaned_data["issue_date"],
                "election_hash": {"a": "hash/sha256/value", "value": self.election.hash},
                "election_uuid": self.election.uuid
            }
            i = 0
            for question in self.election.questions:
                q_answer =self.data['question%d' % i]
                data["proofs"].append(dict(
                    commitment=q_answer['commitment'],
                    response=q_answer['response'],
                    challenge=q_answer['challenge']
                ))
                data["choices"].append(dict(
                    alpha=q_answer['alpha'],
                    beta=q_answer['beta']
                ))
                i += 1
        else:
            data = {
                "a": "plaintext-vote-v1",
                "answers": [],
                "unique_randomness": self.cleaned_data["unique_randomness"],
                "election_hash": {"a": "hash/sha256/value", "value": self.election.hash},
                "election_uuid": self.election.uuid
            }
            i = 0
            for question in self.election.questions:
                data["answers"] += [self.cleaned_data['question%d' % i]]
                i += 1

        # fill the vote
        vote.voter = self.user
        vote.election = self.election
        vote.is_direct = True

        # stablish if the vote is secret
        if self.election.is_vote_secret() and self.cleaned_data['is_vote_secret']:
            vote.is_public = False
            vote.reason = None
        else:
            vote.reason = clean_html(self.cleaned_data['reason'])
            vote.is_public = True

        # assign data, create hash etc
        vote.data = data
        vote.casted_at_date = timezone.now()
        vote.create_hash()
        vote.save()

        # send mail
        if  vote.is_counted:
            # create action
            if not settings.ANONYMIZE_USERS:
                actstream_action.send(self.user, verb='voted', action_object=self.election,
                    target=self.election.agora,
                    geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

                vote.action_id = Action.objects.filter(actor_object_id=self.user.id,
                    verb='voted', action_object_object_id=self.election.id,
                    target_object_id=self.election.agora.id).order_by('-timestamp').all()[0].id

            context = get_base_email_context(self.request)
            context.update(dict(
                to=self.user,
                election=self.election,
                election_url=self.election.get_link(),
                agora_url=self.election.get_link()
            ))

            if self.user.has_perms('receive_email_updates'):
                translation.activate(self.user.get_profile().lang_code)
                email = EmailMultiAlternatives(
                    subject=_('Vote casted for election %s') % self.election.pretty_name,
                    body=render_to_string('agora_core/emails/vote_casted.txt',
                        context),
                    to=[self.user.email])

                email.attach_alternative(
                    render_to_string('agora_core/emails/vote_casted.html',
                        context), "text/html")
                email.send()
                translation.deactivate()

            if not is_following(self.user, self.election):
                follow(self.user, self.election, actor_only=False, request=self.request)
        else:
            profile = self.user.get_profile()
            if not isinstance(profile.extra, dict):
                profile.extra = dict()
            profile.extra['pending_ballot_id'] = vote.id
            profile.extra['pending_ballot_status_%d' % vote.id] = 'unconfirmed'
            profile.save()

            token = default_token_generator.make_token(self.user)

            context = get_base_email_context(self.request)
            confirm_vote_url = self.request.build_absolute_uri(
                reverse('confirm-vote-token',
                    kwargs=dict(username=self.user.username, token=token)))
            context.update(dict(
                to=self.user,
                election=self.election,
                election_url=self.election.get_link(),
                agora_url=self.election.agora.get_link(),
                vote_hash=vote.hash,
                confirm_vote_url=confirm_vote_url
            ))
            translation.activate(self.user.get_profile().lang_code)
            email = EmailMultiAlternatives(
                subject=_('Please confirm vote casted for election %s') % self.election.pretty_name,
                body=render_to_string('agora_core/emails/confirm_vote_casted.txt',
                    context),
                to=[self.user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/confirm_vote_casted.html',
                    context), "text/html")
            email.send()
            translation.deactivate()


        return vote

    class Meta:
        model = CastVote
        fields = ('reason',)


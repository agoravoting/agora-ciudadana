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
from agora_site.agora_core.tasks.election import (start_election, end_election,
    send_election_created_mails)
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
from django.contrib.comments.forms import CommentSecurityForm
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.utils import simplejson as json
from django.utils import translation
from django.contrib.sites.models import Site
from django.db import transaction

import uuid
import datetime
import random


class VoteForm(django_forms.ModelForm):
    '''
    Given an election, creates a form that lets the user choose the options
    he want to vote
    '''
    is_vote_secret = django_forms.BooleanField(required=False)

    def __init__(self, request, election, *args, **kwargs):
        super(VoteForm, self).__init__(*args, **kwargs)
        self.election = election
        self.request = request

        i = 0
        for question in election.questions:
            answers = [(answer['value'], answer['value'])
                for answer in question['answers']]
            random.shuffle(answers)

            self.fields.insert(0, 'question%d' % i, django_forms.ChoiceField(
                label=question['question'], choices=answers, required=True))
            i += 1

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        election = get_object_or_404(Election, pk=kwargs["electionid"])
        return dict(request=request, election=election, data=data)

    def clean(self):
        cleaned_data = super(VoteForm, self).clean()

        if not 'is_vote_secret' in self.data:
            raise forms.ValidationError("is_vote_secret is a required field.")

        cleaned_data['is_vote_secret'] = bool(self.data['is_vote_secret'])

        if not self.election.ballot_is_open():
            raise forms.ValidationError("Sorry, you cannot vote in this election.")

        if cleaned_data['is_vote_secret'] and\
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
        old_votes = self.election.cast_votes.filter(is_direct=True,
            invalidated_at_date=None, voter=self.request.user)
        for old_vote in old_votes:
            old_vote.invalidated_at_date = datetime.datetime.now()
            old_vote.is_counted = False
            old_vote.save()
        vote = super(VoteForm, self).save(commit=False)

        # generate vote
        data = {
            "a": "vote",
            "answers": [],
            "election_hash": {"a": "hash/sha256/value", "value": self.election.hash},
            "election_uuid": self.election.uuid
        }
        i = 0
        for question in self.election.questions:
            data["answers"] += [{
                "a": "plaintext-answer",
                "choices": [self.cleaned_data['question%d' % i]],
            }]
            i += 1

        # fill the vote
        vote.voter = self.request.user
        vote.election = self.election
        vote.is_counted = self.election.has_perms('vote_counts', self.request.user)
        vote.is_direct = True

        # stablish if the vote is secret
        if self.election.is_vote_secret and self.cleaned_data['is_vote_secret']:
            vote.is_public = False
            vote.reason = None
        else:
            vote.reason = self.cleaned_data['reason']
            vote.is_public = True

        # assign data, create hash etc
        vote.data = data
        vote.casted_at_date = datetime.datetime.now()
        vote.create_hash()

        # create action
        actstream_action.send(self.request.user, verb='voted', action_object=self.election,
            target=self.election.agora,
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        vote.action_id = Action.objects.filter(actor_object_id=self.request.user.id,
            verb='voted', action_object_object_id=self.election.id,
            target_object_id=self.election.agora.id).order_by('-timestamp').all()[0].id

        # send email

        vote.save()

        context = get_base_email_context(self.request)
        context.update(dict(
            to=self.request.user,
            election=self.election,
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

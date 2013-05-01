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
from django.utils import timezone
from django.contrib.sites.models import Site
from django.db import transaction

import uuid
import datetime
import random


class DelegateVoteForm(django_forms.ModelForm):
    '''
    Delegates the vote in an agora into a given user
    '''

    # id of the user in which the user whishes to delegate
    user_id = django_forms.IntegerField(required=True)

    def __init__(self, request, agora, *args, **kwargs):
        super(DelegateVoteForm, self).__init__(*args, **kwargs)
        self.agora = agora
        self.request = request

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        agora = get_object_or_404(Agora, pk=kwargs["agoraid"])
        return dict(request=request, agora=agora, data=data)

    def clean_user_id(self, *args, **kwargs):
        self.delegate = get_object_or_404(User, pk=self.cleaned_data['user_id'])
        if self.delegate == self.request.user:
            raise django_forms.ValidationError("Sorry, you cannot delegate into"
                "yourself.")
        return self.delegate.id

    def bundle_obj(self, vote, request):
        from agora_site.agora_core.resources.castvote import CastVoteResource
        cvr = CastVoteResource()
        bundle = cvr.build_bundle(obj=vote, request=self.request)
        bundle = cvr.full_dehydrate(bundle)
        return bundle

    def save(self, *args, **kwargs):
        # invalidate older votes from the same voter to the same election
        old_votes = self.agora.delegation_election.cast_votes.filter(
            is_direct=False, invalidated_at_date=None, voter=self.request.user)
        for old_vote in old_votes:
            old_vote.invalidated_at_date = timezone.now()
            old_vote.save()

        # Forge the delegation vote
        vote = CastVote()
        vote.data = {
            "a": "delegated-vote",
            "answers": [
                {
                    "a": "plaintext-delegate",
                    "choices": [
                        {
                            'user_id': self.delegate.id, # id of the User in which the voter delegates
                            'username': self.delegate.username,
                            'user_name': self.delegate.first_name, # data of the User in which the voter delegates
                        }
                    ]
                }
            ],
            "election_hash": {"a": "hash/sha256/value", "value": self.agora.delegation_election.hash},
            "election_uuid": self.agora.delegation_election.uuid
        }

        vote.voter = self.request.user
        vote.election = self.agora.delegation_election
        vote.is_counted = True # if the user can delegate, it means vote counts
        vote.is_direct = False
        vote.is_public = not self.agora.is_vote_secret
        vote.casted_at_date = timezone.now()
        vote.reason = self.cleaned_data['reason'] if not self.agora.is_vote_secret else ''
        vote.create_hash()
        vote.save()

        # Create the delegation action
        actstream_action.send(self.request.user, verb='delegated', action_object=vote,
            target=self.agora, ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        vote.action_id = Action.objects.filter(actor_object_id=self.request.user.id,
            verb='delegated', action_object_object_id=vote.id,
            target_object_id=self.agora.id).order_by('-timestamp').all()[0].id


        # Send the email to the voter (and maybe to the delegate too!)
        context = get_base_email_context(self.request)
        context.update(dict(
            agora=self.agora,
            delegate=self.delegate,
            vote=vote
        ))

        # Mail to the voter
        if vote.voter.get_profile().has_perms('receive_email_updates'):
            translation.activate(self.request.user.get_profile().lang_code)
            context['to'] = vote.voter

            email = EmailMultiAlternatives(
                subject=_('%(site)s - You delegated your vote in %(agora)s') %\
                    dict(
                        site=Site.objects.get_current().domain,
                        agora=self.agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/user_delegated.txt',
                    context),
                to=[vote.voter.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/user_delegated.html',
                    context), "text/html")
            translation.deactivate()
            email.send()

        if vote.is_public and self.delegate.get_profile().has_perms('receive_email_updates'):
            translation.activate(self.request.user.get_profile().lang_code)
            context['to'] = self.delegate

            email = EmailMultiAlternatives(
                subject=_('%(site)s - You have a new delegation in %(agora)s') %\
                    dict(
                        site=Site.objects.get_current().domain,
                        agora=self.agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/new_delegation.txt',
                    context),
                to=[self.delegate.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/new_delegation.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        if not is_following(self.request.user, self.delegate) and vote.is_public:
            follow(self.request.user, self.delegate, actor_only=False,
                request=self.request)

        return vote

    class Meta:
        model = CastVote
        fields = ('reason',)
 

import os
import re
import datetime
import uuid
import hashlib
import simplejson

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from userena.models import UserenaLanguageBaseProfile
from guardian.shortcuts import *

from agora_site.misc.utils import JSONField, get_users_with_perm
from agora_site.agora_core.models import Election


class CastVote(models.Model):
    '''
    Represent a vote casted in an election. 

    Note that users can vote multiple times in an election; the last vote is
    what matters
    '''
    voter = models.ForeignKey(User, related_name='cast_votes',
        verbose_name=_('Voter'))

    election = models.ForeignKey(Election, related_name='cast_votes',
        verbose_name=_('Election'))

    # This field is false for votes from delegates who are not member of the
    # agora. It's also false if the voter after emitting this vote, he emitted
    # another one. At that point, vote is invalidated.
    is_counted = models.BooleanField(_('Is vote counted'))

    is_direct = models.BooleanField(_('Is a direct vote'))

    # If it's public, you will be able to delegate on it
    is_public = models.BooleanField(_('Is a public vote'))

    # cache the hash of the vote
    hash = models.CharField(max_length=100, unique=True)

    # a tiny version of the hash to enable short URLs
    tiny_hash = models.CharField(max_length=50, null=True, unique=True)

    # only for delegates
    reason = models.TextField(_('Why'), null=True, blank=True)

    action_id = models.IntegerField(unique=True, null=True)

    class Meta:
        app_label = 'agora_core'

    def get_serializable_data(self):
        return {
            'voter_username': self.voter.username,
            'data': self.data,
            'casted_at_date': self.casted_at_date.isoformat()
        }

    def get_serialized(self):
        return simplejson.dumps(self.get_serializable_data())

    def create_hash(self):
        self.hash = hashlib.sha256(self.get_serialized()).hexdigest()
        return self.hash

    # contains the actual vote in JSON format
    # something like:
    #{
        #"a": "vote",
        #"answers": [
            #{
                #"a": "plaintext-answer",
                #"choices": ["Alice", "Bob", ...],
            #},
            #...
        #],

        #"election_hash": {"a": "hash/sha256/value", "value": "Nz1fWLvVLH3eY3Ox7u5hxfLZPdw"},
        #"election_uuid": "1882f79c-65e5-11de-8c90-001b63948875"}
    #}
    # Or in case of a delegation:
    #{
        #"a": "delegated-vote",
        #"answers": [
            #{
                #"a": "plaintext-delegate",
                #"choices": [
                    #{
                        #'user_id': 13, # id of the User in which the voter delegates
                        #'username': 'edulix',
                        #'first_name': 'Eduardo Robles Elvira', # data of the User in which the voter delegates
                        #'user_image_url': 'xx' # data of the User in which the voter delegates
                    #},
                    #...
                #],
            #},
            #...
        #],

        #"election_hash": {"a": "hash/sha256/value", "value": "Nz1fWLvVLH3eY3Ox7u5hxfLZPdw"},
        #"election_uuid": "1882f79c-65e5-11de-8c90-001b63948875"}
    #}
    data = JSONField(_('Data'))

    invalidated_at_date = models.DateTimeField(null=True)

    casted_at_date = models.DateTimeField()

    def is_changed_vote(self):
        '''
        Returns true if before this vote was emitted by the user in this election,
        he emitted a previous one
        '''
        return CastVote.objects.filter(election=self.election, voter=self.voter,
            casted_at_date__lt=self.casted_at_date).count() > 0

    class Meta:
        '''
        A voter can vote multiple times in an election, but only last vote will
        count.
        Also, in a delegates type of election, votes are frozen per election
        taking the last available vote at the time as the reference vote.
        '''
        unique_together = (('election', 'voter', 'casted_at_date'),)
        app_label = 'agora_core'

    def get_delegation_agora(self):
        return self.delegation_agora[0]

    def is_plaintext(self):
        if self.data['a'] == 'vote':
            return self.data['answers'][0]['a'] == 'plaintext-answer'
        elif self.data['a'] == 'delegated-vote':
            return True
        else:
            return True

    def get_delegate(self):
        if self.data['a'] != 'delegated-vote' or not self.is_plaintext():
            raise Exception('This kind of vote does not have delegate user')
        else:
            return get_object_or_404(User, username=self.get_delegate_id())

    def get_delegate_id(self):
        if self.data['a'] != 'delegated-vote' or not self.is_plaintext():
            raise Exception('This kind of vote does not have delegate user')
        else:
            return self.data['answers'][0]['choices'][0]['username']

    def get_chained_first_pretty_answer(self, election=None):
        if not self.is_public:
            raise Exception('Vote is not public')
        elif self.data['a'] == 'vote':
            if self.data['answers'][0]['a'] != 'plaintext-answer':
                raise Exception('Invalid direct vote')

            question_title = self.election.questions[0]['question']
            return dict(question=question_title,
                answer=self.data['answers'][0]['choices'][0],
                reason=self.reason)
        elif self.data['a'] == 'delegated-vote':
            if self.data['answers'][0]['a'] != 'plaintext-delegate':
                raise Exception('Invalid delegated vote')

            delegate = self.get_delegate()
            delegate_vote = delegate.get_profile().get_vote_in_election(election)
            if delegate_vote:
                return delegate_vote.get_chained_first_pretty_answer(election)
            else:
                return None
        else:
            raise Exception('Invalid vote')

    def get_first_pretty_answer(self):
        if not self.is_public:
            raise Exception('Vote is not public')
        elif self.data['a'] == 'vote':
            if self.data['answers'][0]['a'] != 'plaintext-answer':
                raise Exception('Invalid direct vote')

            question_title = self.election.questions[0]['question']
            return dict(question=question_title,
                answer=self.data['answers'][0]['choices'][0])

        elif self.data['a'] == 'delegated-vote':
            if self.data['answers'][0]['a'] != 'plaintext-delegate':
                raise Exception('Invalid delegated vote')

            return dict(
                username=self.data['answers'][0]['choices'][0]['username'],
                first_name=self.data['answers'][0]['choices'][0]['first_name']
            )
        else:
            raise Exception('Invalid vote')

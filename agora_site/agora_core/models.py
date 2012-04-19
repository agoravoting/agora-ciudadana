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

import os
import re
import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from userena.models import UserenaLanguageBaseProfile
from agora_site.misc.utils import JSONField

class Profile(UserenaLanguageBaseProfile):
    '''
    Profile used together with django User class, and accessible via
    user.get_profile(), because  in settings we have configured:

    AUTH_PROFILE_MODULE = 'agora_site.agora_core.models.Profile'

    See https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-AUTH_PROFILE_MODULE
    for more details.
    '''
    user = models.OneToOneField(User)

    def get_fullname(self):
        '''
        Returns the full user name
        '''
        if self.user.last_name:
            return self.user.first_name + ' ' + self.user.last_name
        else:
            return self.user.first_name

    short_description = models.CharField(_('Short Description'), max_length=140)

    biography = models.TextField(_('Biography'))

    # This marks the date of the last activity item known to be read by the user
    # so that later on we can for example send to the user update email only
    # showing activity from this date on
    last_activity_read_date = models.DateTimeField(_(u'Last Activity Read Date'), auto_now_add=True, editable=True)

    # Saving the user language allows sending emails to him in his desired
    # language (among other things)
    lang_code = models.CharField(_("Language Code"), max_length=10, default='')

    email_updates = models.BooleanField(_("Receive email updates"),
        default=True)

    # Stores extra data
    # it will something like:
    #{
        #'type': '2012/04/ProfileExtraData',
        #'data': [
            #{'key': 'Foo', 'value': 'Bar'},
        #]
    #}
    extra = JSONField(_('Extra'), null=True)

from django.db.models.signals import post_save

# definition of UserProfile from above
# ...

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)

class Agora(models.Model):
    '''
    Represents an Agora, formed by a group of people which can vote and delegate
    '''
    ELECTION_TYPES = (
        ('ONCE_CHOICE', _('Simple one choice result type of election')),
        ('SIMPLE_DELEGATION', _('Simple election for delegates where only one delegate can be chosen')),
    )

    MEMBERSHIP_TYPE = (
        ('ANYONE_CAN_JOIN', _('Anyone can join')),
        #('JOINING_REQUIRES_ADMINS_APPROVAL', _('Joining requires admins approval')),
        #('INVITATION_ONLY', _('Invitation only by admins')),
        #('EXTERNAL', _('External url')),
    )

    creator = models.ForeignKey(User, related_name='created_agoras',
        verbose_name=_('Creator'), null=False)

    # TODO: Add this field when we add support for owner transference and start
    # using it
    #owner = models.ForeignKey(User, related_name='owned_agoras',
        #verbose_name=_('Owner'), null=False)

    # Link to the special election where votes are casted
    delegation_election = models.ForeignKey('Election', related_name='delegation_agora',
        verbose_name=_('Delegation Election'), null=True)

    created_at_date = models.DateTimeField(_(u'Created at date'),
        auto_now=True, auto_now_add=True)

    archived_at_date = models.DateTimeField(_(u'Archived at Date'), auto_now_add=False, default=None, null=True)

    # Used for urls, can be autocalculated by default
    name = models.CharField(_('name'), max_length=70, blank=False)

    pretty_name = models.CharField(_('Pretty Name'), max_length=140, blank=False)

    def create_name(self, creator):
        '''
        Using the pretty name, creates an unique name for a given creator
        '''
        name = base_name = re.sub("[^a-zA-Z]+", "-", self.pretty_name)
        i = 2
        while Agora.objects.filter(creator=creator, name=name).count() > 0:
            name = base_name + str(i)
            i += 1
        self.name = name
        return self.name

    short_description = models.CharField(_('Short Description'), max_length=140)

    biography = models.TextField(_('Biography'), default='', blank=True)

    image_url = models.URLField(_('Image Url'), default='', blank=True)

    def get_mugshot_url(self):
        '''
        Either returns image_url or a default image
        '''
        if self.image_url:
            return self.image_url
        else:
            return settings.STATIC_URL + 'img/agora_default_logo.png'

    def get_open_elections(self):
        '''
        Returns the list of current and future elections that will or are
        taking place.
        '''
        return self.elections.filter(
            voting_extended_until_date__gt=datetime.datetime.now()).order_by(
                'voting_extended_until_date', 'voting_starts_at_date')

    def get_tallied_elections(self):
        '''
        Returns the list of past elections with a given result
        '''
        return self.elections.filter(
            result_tallied_at_date__lt=datetime.datetime.now()).order_by(
                '-voting_extended_until_date')

    def grouped_by_date_open_elections(self):
        '''
        Same list of elections as in get_open_elections, but grouped by
        relevant dates, in a list of pairs like:

            dict(date1=(election1, election2, ...), date2=(election3, election4, ...))
        '''

        elections = self.get_open_elections()

        grouping = dict()
        last_date = None

        for election in elections:
            end_date = election.voting_extended_until_date.date()
            start_date = election.voting_starts_at_date.date()

            if start_date not in grouping:
                grouping[start_date] = (election,)
            elif election not in grouping[start_date]:
                grouping[start_date] += (election,)

            if start_date != end_date:
                if end_date not in grouping:
                    grouping[end_date] = (election,)
                elif election not in grouping[end_date]:
                    grouping[end_date] += (election,)

        return grouping

    # Stablishes a default option for elections
    is_vote_secret = models.BooleanField(_('Is Vote Secret'), default=False)

    # Stablishes a default option for elections
    #use_voter_aliases = models.BooleanField(_('Use Voter Aliases'), default=False)

    # Stablishes a default option for elections
    election_type = models.CharField(max_length=50, choices=ELECTION_TYPES,
        default=ELECTION_TYPES[0][0])

    # Stablishes a default option for elections
    # eligibility is a JSON field, which lists auth_systems and eligibility details for that auth_system, e.g.
    # [{'auth_system': 'cas', 'constraint': [{'year': 'u12'}, {'year':'u13'}]}, {'auth_system' : 'password'}, {'auth_system' : 'openid',  'constraint': [{'host':'http://myopenid.com'}]}]
    eligibility = JSONField(null=True)

    membership_policy = models.CharField(max_length=50, choices=MEMBERSHIP_TYPE,
        default=MEMBERSHIP_TYPE[0][0])

    members = models.ManyToManyField(User, related_name='agoras',
        verbose_name=_('Members'))

    admins = models.ManyToManyField(User, related_name='adminstrated_agoras',
        verbose_name=_('Administrators'))

    # Stores extra data
    # it will something like:
    #{
        #'type': '2012/04/AgoraExtraData',
        #'data': [
            #{'key': 'Foo', 'value': 'Bar'},
        #]
    #}
    extra_data = JSONField(_('Extra Data'), null=True)

    class Meta:
        '''
        name of the agora is unique for a given creator
        '''
        unique_together = (('name', 'creator'),)

    def active_delegates(self):
        '''
        Returns the QuerySet with the active delegates
        '''
        # TODO, returning only the members is not accurate, because non-members
        # can also be a delegate. It should be more like "anyone who is a member
        # OR has ever voted even not being a member", and it should be sorted
        # by last vote
        return self.members

class Election(models.Model):
    '''
    Represents an election.

    Recurrent elections are created as linked elections
    to a parent one. Parent election should always be the first in time in a group
    of recurrent/linked elections, i.e. the one with no parent election.
    '''

    # cache the hash of the election
    hash = models.CharField(max_length=100, unique=True)

    # a tiny version of the hash to enable short URLs
    tiny_hash = models.CharField(max_length=50, null=True, unique=True)

    # an election is always related to an agora, except if it's a delegated election
    agora = models.ForeignKey('Agora', related_name='elections',
        verbose_name=_('Agora'), null=True)

    creator = models.ForeignKey(User, related_name='created_elections',
        verbose_name=_('Creator'), blank=False)

    # We might need to freeze the list of voters so that if someone signs in,
    # he cannot vote.
    # NOTE that on a voting of type SIMPLE_DELEGATION, the list is unused,
    # because it's dynamic (changes)
    electorate = models.ManyToManyField(User, related_name='elections',
        verbose_name=_('Electorate'))

    parent_election = models.ForeignKey('self', related_name='children_elections',
        verbose_name=_('Parent Election'), default=None, null=True)

    created_at_date = models.DateTimeField(_(u'Created at date'),
        auto_now=True, auto_now_add=True)

    last_modified_at_date = models.DateTimeField(_(u'Last Modified at Date'), auto_now_add=True, editable=True)

    voting_starts_at_date = models.DateTimeField(_(u'Voting Starts Date'), auto_now_add=False, default=None, null=True)

    voting_ends_at_date = models.DateTimeField(_(u'Voting Ends Date'), auto_now_add=False, default=None, null=True)

    voting_extended_until_date = models.DateTimeField(_(u'Voting Extended until Date'), auto_now_add=False, default=None, null=True)

    approved_at_date = models.DateTimeField(_(u'Approved at Date'), auto_now_add=False, default=None, null=True)

    frozen_at_date = models.DateTimeField(_(u'Frozen at Date'), auto_now_add=False, default=None, null=True)

    archived_at_date = models.DateTimeField(_(u'Archived at Date'), auto_now_add=False, default=None, null=True)

    delegated_votes_frozen_at_date = models.DateTimeField(_(u'Delegated Votes at Date'), auto_now_add=False, default=None, null=True)

    voters_frozen_at_date = models.DateTimeField(_(u'Voters Frozen at Date'), auto_now_add=False, default=None, null=True)

    result_tallied_at_date = models.DateTimeField(_(u'Result Tallied at Date'), auto_now_add=False, default=None, null=True)

    # contains the actual result in JSON format
    # something like:
    #{
        #'type': '2012/04/ElectionResult',
        #'data': [
            #{'id': '0', 'description': 'Yes', 'votes': 7512, 'percent': 75.12},
            #{'id': '1', 'description': 'No', 'votes': 1078, 'percent': 10.78},
            #{'id': '2', 'description': 'Abstention', 'votes': 50, 'percent': 5.0},
        #]
    #}
    result = JSONField(_('Direct Votes Result'), null=True)

    # This will be stored not in the delegation election, but in the
    # normal election which will store both the result and the delegated votes
    # result
    delegated_votes_result = JSONField(_('Delegates Result'), null=True)

    # List of votes linked to the delegation voting of the related agora
    delegated_votes = models.ForeignKey('CastVote',
        related_name='related_elections', verbose_name=_('Delegated Votes'), null=True)

    name = models.CharField(_('Name'), max_length=140)

    short_description = models.CharField(_('Short Description'), max_length=140)

    description = models.TextField(_('Description'))

    # This is a JSONField similar to what is used in helios. For now,
    # it will something like:
    #{
        #'type': '2012/04/PlainTextChoices',
        #'data': [
            #{'id': '0', 'description': 'Yes'},
            #{'id': '1', 'description': 'No'},
            #{'id': '1', 'description': 'Abstention'}
        #]
    #}
    # NOTE that on a voting of type SIMPLE_DELEGATION, the choices list is
    # unused, because it's dynamic (changes)
    choices = JSONField(_('Choices'), null=True)

    is_vote_secret = models.BooleanField(_('Is Vote Secret'), default=False)

    #use_voter_aliases = models.BooleanField(_('Use Voter Aliases'), default=False)

    election_type = models.CharField(max_length=50, choices=Agora.ELECTION_TYPES,
        default=Agora.ELECTION_TYPES[0][0])

    # eligibility is a JSON field, which lists auth_systems and eligibility details for that auth_system, e.g.
    # [{'auth_system': 'cas', 'constraint': [{'year': 'u12'}, {'year':'u13'}]}, {'auth_system' : 'password'}, {'auth_system' : 'openid',  'constraint': [{'host':'http://myopenid.com'}]}]
    eligibility = JSONField(null=True)

    # Stores extra data
    # it will something like:
    #{
        #'type': '2012/04/ElectionExtraData',
        #'data': [
            #{'key': 'Foo', 'value': 'Bar'},
        #]
    #}
    extra_data = JSONField(_('Extra Data'), null=True)

    def get_winning_option(self):
        '''
        Returns data of the winning option or throw an exception
        '''
        if not self.result:
            raise Exception('Election not tallied yet')
        elif self.result['type'] != '2012/04/ElectionResult':
            raise Exception('Unknown election result type: %s' % self.result['type'])

        winner = dict(id=-1,  description='', votes=0.0, percent=0.0)
        for item in self.result['data']:
            if item['votes'] > winner['votes']:
                winner = item

        return winner

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

    # cache the hash of the vote
    hash = models.CharField(max_length=100, unique=True)

    # a tiny version of the hash to enable short URLs
    tiny_hash = models.CharField(max_length=50, null=True, unique=True)

    # contains the actual vote in JSON format
    # something like:
    #{
        #'type': '2012/04/PlainTextCastVote',
        #'data': [
            #{'id': '0', 'description': 'Yes'}
        #]
    #}
    # Or in case of a delegation:
    #{
        #'type': '2012/04/PlainTextCastDelegatedVote',
        #'data': [
            #{'id': '13', # id of the User in which the voter delegates
            #'name': 'Eduardo Robles Elvira', # data of the User in which the voter delegates
            #'image_url': 'xx' # data of the User in which the voter delegates}
        #]
    #}
    data = JSONField(_('Data'))

    invalidated_at_date = models.DateTimeField(null=True)

    casted_at_date = models.DateTimeField(auto_now=True, auto_now_add=True)

    class Meta:
        '''
        A voter can vote multiple times in an election, but only last vote will
        count.
        Also, in a delegates type of election, votes are frozen per election
        taking the last available vote at the time as the reference vote.
        '''
        unique_together = (('election', 'voter', 'casted_at_date'),)

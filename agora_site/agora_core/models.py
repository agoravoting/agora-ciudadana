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
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
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
    extra = JSONField(_('Extra'), null=True)

    def get_open_elections(self):
        '''
        Returns the list of current and future elections that will or are
        taking place in our agoras.
        '''
        return Election.objects.filter(
            Q(voting_extended_until_date__gt=datetime.datetime.now()) |
            Q(voting_extended_until_date=None, voting_starts_at_date__lt=datetime.datetime.now()),
            Q(is_approved=True, agora__in=self.user.agoras.all())
            ).order_by('voting_extended_until_date',
                'voting_starts_at_date')

    def get_requested_elections(self):
        '''
        Returns the list of requested elections related to us.
        '''
        return Election.objects.filter(
            Q(agora__in=self.user.adminstrated_agoras.all()) | Q(creator=self.user),
            Q(is_approved=False) | Q(result_tallied_at_date=None)
        ).order_by('voting_extended_until_date', 'voting_starts_at_date')

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

    # TODO: add a field for banning users

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
        name = base_name = slugify(self.pretty_name[:65])
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
            Q(voting_extended_until_date__gt=datetime.datetime.now()) |
                Q(voting_extended_until_date=None,
                    voting_starts_at_date__lt=datetime.datetime.now()),
            Q(is_approved=True)).order_by('voting_extended_until_date',
                'voting_starts_at_date')

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

            if end_date and start_date != end_date:
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


    def approved_elections(self):
        '''
        Returns the QuerySet with the approved elections
        '''
        return self.elections.filter(is_approved=True)


    def requested_elections(self):
        '''
        Returns the QuerySet with the not approved election
        '''
        return self.elections.filter(is_approved=False)

class Election(models.Model):
    '''
    Represents an election.

    Recurrent elections are created as linked elections
    to a parent one. Parent election should always be the first in time in a group
    of recurrent/linked elections, i.e. the one with no parent election.
    '''

    # Prohibited because the urls would be a mess
    PROHIBITED_ELECTION_NAMES = ('new', 'delete', 'remove', 'election', 'admin', 'view', 'edit')

    # cache the hash of the election. It will be null until frozen
    hash = models.CharField(max_length=100, unique=True, null=True)

    # a tiny version of the hash
    tiny_hash = models.CharField(max_length=50, null=True, unique=True)

    uuid = models.CharField(max_length=50, unique=True)

    url = models.CharField(max_length=300, unique=True)

    # an election is always related to an agora, except if it's a delegated election
    agora = models.ForeignKey('Agora', related_name='elections',
        verbose_name=_('Agora'), null=True)

    creator = models.ForeignKey(User, related_name='created_elections',
        verbose_name=_('Creator'), blank=False)

    # We might need to freeze the list of voters so that if someone signs in,
    # he cannot vote.
    # NOTE that on a voting of type SIMPLE_DELEGATION, the list is unused,
    # because it's dynamic (changes).
    # Usually the electorate is set when election is frozen
    electorate = models.ManyToManyField(User, related_name='elections',
        verbose_name=_('Electorate'))

    parent_election = models.ForeignKey('self', related_name='children_elections',
        verbose_name=_('Parent Election'), default=None, null=True)

    created_at_date = models.DateTimeField(_(u'Created at date'),
        auto_now=True, auto_now_add=True)

    is_vote_secret = models.BooleanField(_('Is Vote Secret'), default=False)

    is_approved = models.BooleanField(_('Is Approved'), default=False)

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
        #"a": "result",
        #"counts": [
            #[
                #<QUESTION_1_CANDIDATE_1_COUNT>, <QUESTION_1_CANDIDATE_2_COUNT>,
                #<QUESTION_1_CANDIDATE_3_COUNT>
            #],
            #[
                #<QUESTION_2_CANDIDATE_1_COUNT>, <QUESTION_2_CANDIDATE_2_COUNT>
            #]
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

    pretty_name = models.CharField(_('Pretty Name'), max_length=140)

    name = models.CharField(_('name'), max_length=70)

    short_description = models.CharField(_('Short Description'), max_length=140,
        help_text=_('Short description of the election (required)'), null=False)

    description = models.TextField(_('Description'), help_text=_('Long description of the election'))

    # This is a JSONField similar to what is used in helios. For now,
    # it will something like:
    #[
        #{
            #"a": "ballot/question",
            #"answers": [
                #{
                    #"a": "ballot/answer",
                    #"value": "Alice",
                    #"url": "<http://alice.com>", # UNUSED ATM
                    #"details": "Alice is a wonderful person who..." # UNUSED ATM
                #},
                #...
            #],
            #"max": 1, "min": 0,
            #"question": "Who Should be President?",
            #"randomize_answer_order": false, # true by default
            #"short_name": "President", # UNSED ATM
            #"tally_type": "simple" 
        #},
        #...
    #]
    # NOTE that on a voting of type SIMPLE_DELEGATION, the choices list is
    # unused, because it's dynamic (changes)
    questions = JSONField(_('Questions'), null=True)

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

    def create_name(self):
        '''
        Using the pretty name, creates an unique name for a given creator
        '''
        name = base_name = slugify(self.pretty_name[:65])
        i = 2
        while Election.objects.filter(agora=self.agora, name=name).count() > 0 or\
            name in Election.PROHIBITED_ELECTION_NAMES:
            name = base_name + str(i)
            i += 1
        self.name = name
        return self.name

    def get_mugshot_url(self):
        '''
        Returns a default image representing the election for now
        '''
        return settings.STATIC_URL + 'img/election_new_form_info.png'

    def has_perms(self, permission_name, user):
        '''
        Return whether a given user has a given permission name, depending on
        also in the state of the election.
        '''
        isadminorcreator = (self.creator == user or\
            self.agora.admins.filter(id=self.creator.id).exists())
        isarchived = self.archived_at_date != None

        if permission_name == 'edit_details':
            return self.voting_starts_at_date == None and isadminorcreator and not isarchived
        elif permission_name == 'begin_election':
            return self.voting_starts_at_date == None and isadminorcreator and not isarchived
        elif permission_name == 'end_election':
            return self.voting_starts_at_date  != None and\
                self.voting_starts_at_date < datetime.datetime.now() and\
                self.voting_ends_at_date == None and isadminorcreator and\
                not isarchived
        elif permission_name == 'archive_election':
            return isadminorcreator

    def get_perms(self, user):
        '''
        Returns a list of permissions for a given user calling to self.has_perms()
        '''
        return [perm for perm in ('edit_details', 'begin_election', 'end_election', 'archive_election') if self.has_perms(perm, user)]

    def ballot_is_open(self):
        '''
        Returns if the ballot is open, i.e. if one can vote. 
        TODO: In the future allow delegates to vote when election is frozen and
        voting hasn't started yet, so that others can delegate in them in
        advance. For now, any voter is a delegate.
        '''
        now = datetime.datetime.now()
        return self.voting_starts_at_date < now and (self.voting_extended_until_date == None or
            self.voting_extended_until_date > now)

    def has_user_voted(self, user):
        '''
        Return true if the user has voted
        '''
        return CastVote.objects.filter(election=self, voter=user).count() > 0

    def get_direct_votes(self):
        '''
        Return the list of direct votes. This is needed because a voter can vote
        twice, so we cannot directly just return self.cast_votes (it can
        contain duplicates)
        '''
        # TODO not return self.cast_votes :-P
        return self.cast_votes

    def get_delegated_votes(self):
        '''
        Return the list of delegated votes, similar to get_direct_votes
        '''
        # TODO
        return self.cast_votes

    def get_all_votes(self):
        '''
        Similar to get_direct_votes, but adding delegated votes into the mix
        '''
        # TODO make a custom query for this
        return self.get_direct_votes().all() + self.get_delegated_votes().all()

    def count_all_votes(self):
        # TODO: exclude votes from people who cannot vote
        return self.get_direct_votes().count() + self.get_delegated_votes().count()

    def percentage_of_participation(self):
        return (self.count_all_votes() * 100.0) / self.agora.members.count()

    def get_brief_description(self):
        desc = _('This voting allows delegation from any party and vote is not secret.')

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
                        #'user_name': 'Eduardo Robles Elvira', # data of the User in which the voter delegates
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

    casted_at_date = models.DateTimeField(auto_now=True, auto_now_add=True)

    class Meta:
        '''
        A voter can vote multiple times in an election, but only last vote will
        count.
        Also, in a delegates type of election, votes are frozen per election
        taking the last available vote at the time as the reference vote.
        '''
        unique_together = (('election', 'voter', 'casted_at_date'),)

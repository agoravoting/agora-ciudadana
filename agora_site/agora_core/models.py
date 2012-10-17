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
import hashlib
import simplejson

from django.conf import settings
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

    def get_first_name_or_nick(self):
        if self.user.first_name:
            return self.user.first_name
        else:
            return self.user.username

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

    def get_open_elections(self, searchquery = None):
        '''
        Returns the list of current and future elections that will or are
        taking place in our agoras.
        '''
        elections = Election.objects.filter(
            Q(voting_extended_until_date__gt=datetime.datetime.now()) |
            Q(voting_extended_until_date=None, voting_starts_at_date__lt=datetime.datetime.now()),
            Q(is_approved=True, agora__in=self.user.agoras.all())).filter(archived_at_date=None)

        if searchquery and len(searchquery) > 1:
            elections = elections.filter(pretty_name__icontains=searchquery)

        return elections.order_by('-voting_extended_until_date',
                '-voting_starts_at_date')

    def get_requested_elections(self):
        '''
        Returns the list of requested elections related to us.
        '''
        return Election.objects.filter(
            Q(agora__in=self.user.administrated_agoras.all()) | Q(creator=self.user),
            Q(is_approved=False) | Q(result_tallied_at_date=None)
        ).filter(archived_at_date=None).exclude(name='delegation').order_by('-voting_extended_until_date', '-voting_starts_at_date')

    def count_direct_votes(self):
        '''
        Returns the list of valid direct votes by this user
        '''
        return CastVote.objects.filter(voter=self.user, is_direct=True, is_counted=True).count()

    def get_participated_elections(self):
        '''
        Returns the list of elections in which the user participated, either
        via a direct or a delegated vote
        '''
        user_direct_votes=CastVote.objects.filter(voter=self.user, is_direct=True, is_counted=True).all()
        user_delegated_votes=CastVote.objects.filter(voter=self.user).all()
        return Election.objects.filter(agora__isnull=False,
            result_tallied_at_date__isnull=False).filter(
                Q(delegated_votes__in=user_delegated_votes) |
                Q(cast_votes__in=user_direct_votes)).order_by('-result_tallied_at_date','-voting_extended_until_date')

    def has_delegated_in_agora(self, agora):
        '''
        Returns whether this user has currently delegated his vote in a given
        agora.
        '''
        return bool(CastVote.objects.filter(voter=self.user, is_direct=False,
            election=agora.delegation_election, is_counted=True).count())

    def get_delegation_in_agora(self, agora):
        '''
        Returns this user current vote regarding his delegation (if any)
        '''
        try:
            return CastVote.objects.filter(voter=self.user, is_direct=False,
                election=agora.delegation_election, is_counted=True).order_by('-casted_at_date')[0]
        except Exception, e:
            return None

    def get_vote_in_election(self, election):
        '''
        Returns the vote of this user in the given agora if any. Note: if the
        vote is a delegated one, this only works for tallied elections.
        '''
        if election.cast_votes.filter(voter=self.user, is_counted=True).count() == 1:
            return election.cast_votes.filter(voter=self.user, is_counted=True)[0]
        else:
            votes = election.delegated_votes.filter(voter=self.user)
            if len(votes) == 0:
                return None

            return votes[0]

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
        ('JOINING_REQUIRES_ADMINS_APPROVAL_ANY_DELEGATE', _('Joining requires admins approval, allow non-member delegates')),
        ('JOINING_REQUIRES_ADMINS_APPROVAL', _('Joining requires admins approval and delegates must be agora members')),
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
            Q(is_approved=True)).order_by('-voting_extended_until_date',
                '-voting_starts_at_date')

    def get_open_elections_with_name_start(self, name):
        '''
        Returns the list of current and future elections that will or are
        taking place, that start with a name.

        Used by ajax endpoint searchElection
        '''
        return self.elections.filter(
            Q(voting_extended_until_date__gt=datetime.datetime.now()) |
                Q(voting_extended_until_date=None,
                    voting_starts_at_date__lt=datetime.datetime.now()),
            Q(is_approved=True),
            Q(pretty_name__icontains=name)).order_by('-voting_extended_until_date',
                '-voting_starts_at_date')

    def get_tallied_elections(self):
        '''
        Returns the list of past elections with a given result
        '''
        return self.elections.filter(
            result_tallied_at_date__lt=datetime.datetime.now()).order_by(
                '-voting_extended_until_date')

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

    admins = models.ManyToManyField(User, related_name='administrated_agoras',
        verbose_name=_('Administrators'))

    # Stores extra data
    extra_data = JSONField(_('Extra Data'), null=True)

    class Meta:
        '''
        name of the agora is unique for a given creator
        '''
        unique_together = (('name', 'creator'),)
        permissions = (
            ('requested_membership', _('Requested membership')),
            ('invited_to_membership', _('Invited to membership')),
            ('requested_admin_membership', _('Requested admin membership')),
        )

    def active_delegates(self):
        '''
        Returns the QuerySet with the active delegates
        '''
        return User.objects.filter(
            id__in=CastVote.objects.filter(is_counted=True, is_direct=True,
                invalidated_at_date=None, election__agora__id=self.id).values('id').query)

    def active_nonmembers_delegates(self):
        '''
        Same as active_delegates but all of those who are not currently a member
        of the agora.
        '''
        return User.objects.filter(
            id__in=CastVote.objects.filter(is_counted=True, is_direct=True,
                invalidated_at_date=None, election__agora__id=self.id)
            )\
            .exclude(id__in=self.members.values('id').query)

    def users_who_requested_membership(self):
        '''
        Returns those users who requested membership in this Agora
        '''
        return get_users_with_perm(self, 'requested_membership')

    def users_who_requested_admin_membership(self):
        '''
        Returns those users who requested admin membership in this Agora
        '''
        return get_users_with_perm(self, 'requested_admin_membership')

    def all_elections(self):
        '''
        Returns the QuerySet with all elections but the delegation one
        '''
        return self.elections.exclude(name__exact='delegation')

    def archived_elections(self):
        '''
        Returns the QuerySet with all archived elections in this agora
        '''
        return self.elections.filter(archived_at_date__isnull=False).exclude(name__exact='delegation')
    

    def approved_elections(self):
        '''
        Returns the QuerySet with the approved elections
        '''
        return self.elections.filter(is_approved=True)

    def open_elections(self):
        '''
        Returns the QuerySet with the open and approved elections
        '''

        return self.elections.filter(
            Q(voting_extended_until_date__gt=datetime.datetime.now()) |
            Q(voting_extended_until_date=None, voting_starts_at_date__lt=datetime.datetime.now()),
            Q(is_approved=True)
        ).order_by('-voting_extended_until_date',
            '-voting_starts_at_date')


    def requested_elections(self):
        '''
        Returns a QuerySet with the not approved elections
        '''
        return self.elections.filter(is_approved=False).exclude(name='delegation')

    @staticmethod
    def static_has_perms(permission_name, user):
        if permission_name == 'create':
            if settings.AGORA_CREATION_PERMISSIONS == 'any-user':
                return True
            elif settings.AGORA_CREATION_PERMISSIONS == 'superusers-only':
                return user.is_superuser
            else:
                return False
        else:
            return False

    def has_perms(self, permission_name, user):
        '''
        Return whether a given user has a given permission name, depending on
        also in the state of the election.
        '''
        opc = ObjectPermissionChecker(user)
        requires_membership_approval = (
            self.membership_policy == Agora.MEMBERSHIP_TYPE[1][0] or\
            self.membership_policy == Agora.MEMBERSHIP_TYPE[2][0]
        )

        if permission_name == 'join':
            return self.membership_policy == Agora.MEMBERSHIP_TYPE[0][0] and\
                not user in self.members.all()
        elif permission_name == 'request_membership':
            return requires_membership_approval and not user in self.members.all() and\
                'requested_membership' not in opc.get_perms(self)
        elif permission_name == "cancel_membership_request":
            return requires_membership_approval and not user in self.members.all() and\
                'requested_membership' in opc.get_perms(self)
        if permission_name == 'request_admin_membership':
            return user in self.members.all() and user not in self.admins.all() and\
                'requested_admin_membership' not in opc.get_perms(self)
        elif permission_name == "cancel_admin_membership_request":
            return user in self.members.all() and user not in self.admins.all() and\
                'requested_admin_membership' in opc.get_perms(self)
        elif permission_name == 'leave':
            return self.creator != user and user in self.members.all() and\
                user not in self.admins.all()
        elif permission_name == 'admin':
            return self.creator == user or user in self.admins.all()
        elif permission_name == 'leave_admin':
            return self.creator != user and user in self.admins.all()

    def get_perms(self, user):
        '''
        Returns a list of permissions for a given user calling to self.has_perms()
        '''
        return [perm for perm in ('join', 'request_membership',
            'cancel_membership_request', 'request_admin_membership',
            'cancel_admin_membership_request', 'leave', 'leave_admin',
            'admin') if self.has_perms(perm, user)]


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

    def task_id(self, task):
        return "election_task_" + str(self.id) + task.name

    def get_serializable_data(self):
        data = {
            'creator_username': self.creator.username,
            'agora_name': self.agora.name,
            'url': self.url,
            'uuid': self.uuid,
            'is_vote_secret': self.is_vote_secret,
            'created_at_date': self.created_at_date.isoformat(),
            'questions': self.questions,
            'election_type': self.election_type,
            'name': self.name,
            'pretty_name': self.pretty_name,
            'description': self.description,
            'short_description': self.short_description,
            'eligibility': self.eligibility
        }

        if self.voting_starts_at_date:
            data['start_date'] = self.voting_starts_at_date.isoformat()

        return data

    def get_serialized(self):
        return simplejson.dumps(self.get_serializable_data())

    def create_hash(self):
        self.hash = hashlib.sha256(self.get_serialized()).hexdigest()
        return self.hash

    # a tiny version of the hash
    tiny_hash = models.CharField(max_length=50, null=True, unique=True)

    uuid = models.CharField(max_length=50, unique=True)

    url = models.CharField(max_length=255, unique=True)

    # an election is always related to an agora, except if it's a delegated election
    agora = models.ForeignKey('Agora', related_name='elections',
        verbose_name=_('Agora'), null=True)

    def is_delegated_election(self):
        return self.name == "delegation"

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

    created_at_date = models.DateTimeField(_(u'Created at date'))

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
    #[
        #{
            #u'a': u'ballot/question',
            #u'tally_type': u'simple',
            #u'max': 1,
            #u'min': 0,
            #u'question': u"What's the next big thing?",
            #u'randomize_answer_order': True,
            #u'answers': [
                #{
                    #u'a': u'ballot/answer',
                    #u'by_delegation_count': 0,
                    #u'by_direct_vote_count': 1,
                    #u'url': u'',
                    #u'value': u'Wadobo',
                    #u'details': u''
                #},
                #{
                    #u'a': u'ballot/answer',
                    #u'by_delegation_count': 0,
                    #u'by_direct_vote_count': 0,
                    #u'url': u'',
                    #u'value': u'Agora',
                    #u'details': u''
                #},
        #},
        #...
    #]
    result = JSONField(_('Election Result'), null=True)

    delegated_votes_result = JSONField(_('Election Delegation Result'), null=True)

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


    delegated_votes = models.ManyToManyField('CastVote', related_name='delegated_votes',
        verbose_name=_('Delegated votes'))

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
        Returns data of the winning option for the first question or throw an exception
        '''
        if not self.result:
            raise Exception('Election not tallied yet')
        elif len(self.result) == 0 or self.result[0]['tally_type'] != 'simple':
            raise Exception('Unknown election result type: %s' % self.result['type'])

        winner = dict(value='', total_count=0.0, total_count_percentage=0.0)

        result = self.get_result_pretty()
        for answer in result[0]['answers']:
            if answer['total_count'] > winner['total_count']:
                winner = answer

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

    def has_started(self):
        '''
        Returns true if voting has started, false otherwise
        '''
        return self.voting_starts_at_date != None and self.voting_starts_at_date < datetime.datetime.now()

    def has_ended(self):
        '''
        Returns true if voting has ended, false otherwise
        '''
        now = datetime.datetime.now()
        if self.voting_extended_until_date == None:
            return self.voting_ends_at_date and  self.voting_ends_at_date < datetime.datetime.now()
        else:
            return self.voting_extended_until_date and self.voting_extended_until_date < datetime.datetime.now()

    def is_archived(self):
        '''
        Returns true if the election has been archived, false otherwise
        '''
        return self.archived_at_date != None

    def is_frozen(self):
        '''
        Returns true if the election has been frozen and thus it cannot be
        editted anymore, false otherwise
        '''
        return self.frozen_at_date != None

    def has_perms(self, permission_name, user):
        '''
        Return whether a given user has a given permission name, depending on
        also in the state of the election.
        '''
        isadmin = self.agora.admins.filter(id=user.id).exists()
        isadminorcreator = (self.creator == user or isadmin)
        isarchived = self.is_archived()
        isfrozen = self.is_frozen()

        if permission_name == 'edit_details':
            return not self.has_started() and isadminorcreator and\
                not isarchived and not isfrozen
        elif permission_name == 'freeze_election':
            return not isfrozen and isadminorcreator and not isarchived
        elif permission_name == 'approve_election':
            return not self.is_approved and isadmin and not isarchived
        elif permission_name == 'begin_election':
            return not self.voting_starts_at_date and isadmin and not isarchived and\
                self.is_approved
        elif permission_name == 'end_election':
            return self.has_started() and not self.voting_ends_at_date and\
                isadmin and not isarchived
        elif permission_name == 'archive_election':
            return isadminorcreator and not isarchived
        elif permission_name == 'comment_election':
            return isadminorcreator or not isarchived and user.is_authenticated()
        elif permission_name == 'emit_direct_vote':
            return user in self.agora.members.all() or\
                self.agora.has_perms('join', user)
        elif permission_name == 'vote_counts':
            return user in self.agora.members.all() or\
                self.agora.has_perms('join', user)
        elif permission_name == 'emit_delegate_vote':
            return user in self.agora.members.all() or\
                self.agora.has_perms('join', user) or\
                self.agora.membership_policy == Agora.MEMBERSHIP_TYPE[1][0]

    def get_perms(self, user):
        '''
        Returns a list of permissions for a given user calling to self.has_perms()
        '''
        return [perm for perm in ('edit_details', 'approve_election',
            'begin_election', 'freeze_election', 'end_election',
            'archive_election', 'comment_election', 'emit_direct_vote',
            'emit_delegate_vote', 'vote_counts') if self.has_perms(perm, user)]

    def ballot_is_open(self):
        '''
        Returns if the ballot is open, i.e. if one can vote. 
        TODO: In the future allow delegates to vote when election is frozen and
        voting hasn't started yet, so that others can delegate in them in
        advance. For now, any voter is a delegate.
        '''
        now = datetime.datetime.now()
        return self.has_started() and not self.has_ended()

    def has_user_voted(self, user):
        '''
        Return true if the user has voted directly
        '''
        if user.is_anonymous():
            return False

        return self.cast_votes.filter(is_counted=True, is_direct=True,
            voter=user).count() > 0

    def get_direct_votes(self):
        '''
        Return the list of direct votes
        '''
        return self.cast_votes.filter(is_counted=True, is_direct=True)

    def get_votes_from_delegates(self):
        '''
        Return the list of votes from delegates.
        '''
        # NOTE: in the future, in an election where encryption is enabled, we
        # will only count here votes from delegates which will be those where
        # is_counted = False, but for now, this means all votes basically:
        # everyone acts as a delegate.
        return self.cast_votes.filter(is_public=True, is_direct=True,
            invalidated_at_date=None)

    def get_all_votes(self):
        '''
        Counts both direct and delegated votes that are counted
        '''

        # TODO: When you have first voted directly in a voting and then you
        # delegate your vote in the agora, it's currently not counted
        if self.ballot_is_open():
            q=self.cast_votes.filter(is_counted=True, is_direct=True, invalidated_at_date=None).values('voter__id').query

            # if ballot is open, we have yet not collected the final list of
            # delegated votes so we get it in real time from
            # agora.delegation_election
            return CastVote.objects.filter(
                # direct votes from people who can vote:
                Q(election=self, is_counted=True, is_direct=True,
                    invalidated_at_date=None)
                # indirect votes from people who have an active delegation in
                # this agora:
                | Q(election=self.agora.delegation_election, is_direct=False,
                    is_counted=True, invalidated_at_date=None)
            # This is to avoid duplicates. If you voted directly, that's what
            # counts:
            ).exclude(is_direct=False, voter__id__in=q).order_by('-casted_at_date')
        else:
            # if ballot is closed, then the delegated votes are already in 
            # self.delegated_votes
            return CastVote.objects.filter(
                # direct votes from people who can vote
                Q(election=self, is_counted=True, is_direct=True,
                    invalidated_at_date=None)
                # delegated votes from people who delegated for this election
                | Q(id__in=self.delegated_votes.values('id').query))
            return self.cast_votes.filter(is_counted=True, invalidated_at_date=None)

    def percentage_of_participation(self):
        '''
        Returns the percentage (0 to 100%) of people that have voted with
        respect to the electorate
        '''
        if self.agora.members.count() > 0:
            return (self.get_all_votes().count() * 100.0) / self.agora.members.count()
        else:
            return 0

    def has_user_voted_via_a_delegate(self, voter):
        vote = self.get_vote_for_voter(voter)
        if not vote:
            return False
        if vote.is_direct == False:
            return True
        return False

    def get_vote_for_voter(self, voter):
        '''
        Given a voter (an User), returns the vote of the vote of this voter
        on the election. It will be either a proxy or a direct vote
        '''
        # These are all the direct votes, even from those who are not elegible
        # to vote in this election
        nodes = self.cast_votes.filter(is_direct=True, invalidated_at_date=None)

        # These are all the delegation votes, i.e. those that point to a delegate
        edges = self.agora.delegation_election.cast_votes.filter(is_direct=False, invalidated_at_date=None)

        if nodes.filter(voter__id=voter.id).count() == 1:
            return nodes.filter(voter__id=voter.id)[0]
        elif edges.filter(voter__id=voter.id).count() == 1:
            return edges.filter(voter__id=voter.id)[0]
        else:
            return None

    def get_brief_description(self):
        '''
        Returns a brief description of the election
        '''

        if self.agora.membership_policy == Agora.MEMBERSHIP_TYPE[0][0]:
            desc = _('This election allows everyone to vote. ')
            desc.__unicode__()
        elif self.agora.membership_policy == Agora.MEMBERSHIP_TYPE[1][0]:
            desc = _('This election only allows agora members to vote. ')
            desc.__unicode__()
        elif self.agora.membership_policy == Agora.MEMBERSHIP_TYPE[2][0]:
            desc = _('This election only allows agora members to vote, but any delegate can emit their position. ')
            desc.__unicode__()

        if self.is_vote_secret:
            tmp = _('Vote is secret (public for delegates). ')
            desc += tmp.__unicode__()
        else:
            tmp = _('Vote is public. ')
            desc += tmp.__unicode__()
        now = datetime.datetime.now()

        def timesince(dati):
            return ('<time class="timeago" title="%(isotime)s" '
                'datetime="%(isotime)s"></time>') % dict(isotime=dati.isoformat())

        if self.is_approved and self.frozen_at_date:
            tmp = (_("The election has been approved and was frozen "
                " %(frozen_date)s. ") % dict(frozen_date=timesince(self.frozen_at_date)))
            desc += tmp
        elif self.is_approved and not self.frozen_at_date:
            tmp = (_("The election has been approved and is not frozen yet. "))
            desc += tmp.__unicode__()
        elif not self.is_approved and self.frozen_at_date:
            tmp = (_("The election has not been approved yet and was frozen "
                " %(frozen_date)s. ") % dict(frozen_date=timesince(self.frozen_at_date)))
            desc += tmp
        elif not self.is_approved and not self.frozen_at_date:
            tmp = (_("The election has been not approved and is not frozen yet. "))
            desc += tmp.__unicode__()

        if self.voting_starts_at_date and self.voting_extended_until_date and\
            not self.has_started():
            tmp = (_("Voting will start  %(start_date)s and finish "
                "%(end_date)s. ") % dict(start_date=timesince(self.voting_starts_at_date),
                    end_date=timesince(self.voting_extended_until_date)))
            desc += tmp
        elif self.voting_starts_at_date and not self.has_started():
            tmp = (_("Voting will start %(start_date)s. ") %\
                dict(start_date=timesince(self.voting_starts_at_date)))
            desc += tmp
        elif self.voting_starts_at_date and self.voting_extended_until_date and\
            self.has_started() and not self.has_ended():
            tmp = (_("Voting started %(start_date)s and will finish "
                "%(end_date)s. ") % dict(start_date=timesince(self.voting_starts_at_date),
                    end_date=timesince(self.voting_extended_until_date)))
            desc += tmp
        elif self.ballot_is_open():
            tmp = (_("Voting started %(start_date)s. ") %\
                dict(start_date=timesince(self.voting_starts_at_date)))
            desc += tmp
        elif self.result_tallied_at_date:
            tmp = (_("Voting started %(start_date)s and finished "
                "%(end_date)s. Results available since %(tally_date)s. ") %\
                    dict(start_date=timesince(self.voting_starts_at_date),
                        end_date=timesince(self.voting_extended_until_date),
                        tally_date=timesince(self.result_tallied_at_date)))
            desc += tmp
        elif not self.voting_starts_at_date:
            tmp = (_("Start date for voting is not set yet. "))
            desc += tmp.__unicode__()

        if self.archived_at_date:
            tmp = (_("Election is <b>archived and dismissed</b>."))
            desc += tmp.__unicode__()
        return desc

    def compute_result(self):
        '''
        Computes the result of the election
        '''

        # Query with the direct votes in this election
        q=self.cast_votes.filter(
            is_counted=True,
            invalidated_at_date=None
        ).values('voter__id').query

        # Query with the delegated votes
        self.delegated_votes = CastVote.objects.filter(
            election=self.agora.delegation_election,
            is_direct=False,
            is_counted=True,
            invalidated_at_date=None
            # we exclude from this query the people who voted directly so that
            # you cannot vote twice
        ).exclude(
            is_direct=False,
            voter__id__in=q
        )

        # These are all the people that can vote in this election
        self.electorate = self.agora.members.all()

        # These are all the direct votes, even from those who are not elegible
        # to vote in this election
        nodes = self.cast_votes.filter(is_direct=True, invalidated_at_date=None)

        # These are all the delegation votes, i.e. those that point to a delegate
        edges = self.agora.delegation_election.cast_votes.filter(is_direct=False, invalidated_at_date=None)

        # list of saved paths
        # A path has the following format:
        #{
            #user_ids: [id1, id2, ...],
            #answers: [ question1_plaintext_answer, question2_plaintext_answer, ..],
            #is_broken_loop: True|False
        #}
        # note that the user_ids do NOT include the last user in the chain
        # also note that is_broken_loop is set to true if either the loop is
        # closed (infinite) or does not end in a leaf (=node)
        paths = []

        # a dictionary where the number of delegated voted per delegate is stored
        # the keys are the user_ids of the delegates, and the keys are the 
        # number of delegated votes
        delegation_counts = dict()

        def update_delegation_counts(vote):
            '''
            function used to update the delegation counts, for each valid vote.
            it basically goes deep in the delegation chain, updating the count
            for each delegate
            '''
            def increment_delegate(delegate_id):
                '''
                Increments the delegate count or sets it to one if doesn't exist
                '''
                if delegate_id in delegation_counts:
                    delegation_counts[delegate_id] += 1
                else:
                    delegation_counts[delegate_id] = 1

            while not vote.is_direct:
                next_delegate = vote.get_delegate()
                if nodes.filter(voter__id=voter.id).count() == 1:
                    increment_delegate(next_delegate.id)
                    return
                elif edges.filter(voter__id=voter.id).count() == 1:
                    increment_delegate(next_delegate.id)
                    vote = edges.filter(voter__id=voter.id)[0]
                else:
                    raise Exception('Broken delegation chain')

        def get_path_for_user(user_id):
            '''
            Given an user id, checks if it's already in any known path, and 
            return it if that path is found. Returns None otherwise.
            '''
            for path in paths:
                if user_id in path["user_ids"]:
                    return path
            return None

        def get_vote_for_voter(voter):
            '''
            Given a voter (an User), returns the vote of the vote of this voter
            on the election. It will be either a proxy or a direct vote
            '''
            if nodes.filter(voter__id=voter.id).count() == 1:
                return nodes.filter(voter__id=voter.id)[0]
            else:
                return edges.filter(voter__id=voter.id)[0]

        if self.election_type != Agora.ELECTION_TYPES[0][0]:
            raise Exception('do not know how to count this type of voting')

        # result is in the same format as get_result_pretty(). Initialized here
        result = self.questions
        for question in result:
            for answer in question['answers']:
                answer['by_direct_vote_count'] = 0
                answer['by_delegation_count'] = 0

        def add_vote(user_answers, is_delegated):
            '''
            Given the answers of a vote, update the result
            '''
            i = 0
            for question in result:
                for answer in question['answers']:
                    if answer['value'] in user_answers[i]["choices"]:
                        if is_delegated:
                            answer['by_delegation_count'] += 1
                        else:
                            answer['by_direct_vote_count'] += 1
                        break
                i += 1

        # Here we go! for each voter, we try to find it in the paths, or in
        # the proxy vote chain, or in the direct votes pool
        for voter in self.electorate.all():
            path_for_user = get_path_for_user(voter.id)

            # Found the user in a known path
            if path_for_user and not path_for_user['is_closed_loop']:
                # found a path to which the user belongs

                # update delegation counts
                update_delegation_counts(self.get_vote_for_voter(voter))
                add_vote(path_for_user['answers'], is_delegated=True)
            # found the user in a direct vote
            elif nodes.filter(voter__id=voter.id).count() == 1:
                vote = nodes.filter(voter__id=voter.id)[0]
                update_delegation_counts(vote)
                add_vote(vote.data["answers"], is_delegated=False)
            # found the user in an edge (delegated vote), but not yet in a path
            elif edges.filter(voter__id=voter.id).count() == 1:
                path = dict(
                    user_ids=[voter.id],
                    answers=[]
                )

                current_edge = edges.filter(voter__id=voter.id)[0]
                loop = True
                while loop:
                    delegate = current_edge.get_delegate()
                    path_for_user = get_path_for_user(delegate.id)

                    if delegate in path['user_ids']:
                        # wrong path! loop found, vote won't be counted
                        path['is_broken_loop'] = True
                        paths += [path]
                        loop = False
                    elif path_for_user and not path_for_user['is_closed_loop']:
                        # extend the found path and count a new vote
                        path_for_user['user_ids'] += path['user_ids']

                        # Count the vote
                        i = 0
                        add_vote(path_for_user['answers'], is_delegated=True)
                        update_delegation_counts(vote)
                        loop = False
                    elif nodes.filter(voter__id=delegate.id).count() == 1:
                        # The delegate voted directly, add the path and count
                        # the vote
                        vote = nodes.filter(voter__id=delegate.id)[0]
                        paths += [path]
                        add_vote(vote.data['answers'], is_delegated=True)
                        update_delegation_counts(vote)
                        loop = False

                    elif edges.filter(voter__id=delegate.id).count() == 1:
                        # the delegate also delegated, so continue looping
                        path['user_ids'] += [delegate.id]
                    else:
                        # broken path! we cannot continue
                        path['is_broken_loop'] = True
                        paths += [path]
                        loop = False

        # all votes counted, finish result
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
        self.result = dict(
            a= "result",
            counts = []
        )


        #{
            #"a": "result",
            #"election_counts": [
                #[
                    #<QUESTION_1_CANDIDATE_1_COUNT>, <QUESTION_1_CANDIDATE_2_COUNT>,
                    #<QUESTION_1_CANDIDATE_3_COUNT>
                #],
                #[
                    #<QUESTION_2_CANDIDATE_1_COUNT>, <QUESTION_2_CANDIDATE_2_COUNT>
                #]
            #],
            # "delegation_counts": [
                #{
                    #'delegate_username': '<DELEGATE_1_USERNAME>',
                    #'count': <DELEGATE_1_COUNT>,
                #},
                #{
                    #'delegate_username': '<DELEGATE_1_USERNAME>',
                    #'count': <DELEGATE_1_COUNT>,
                #}
            # ]
            #
        #}
        self.delegated_votes_result = dict(
            a= "result",
            election_counts = [],
            delegation_counts = [dict(delegate_username=key, count=value)
                for key, value in delegation_counts]
        )
        i = 0
        for question in result:
            j = 0
            question_result = []
            question_delegation_result = []
            for answer in question['answers']:
                question_result += [answer['by_direct_vote_count'] + answer['by_delegation_count']]
                question_delegation_result += [answer['by_delegation_count']]
            self.result['counts'] += [question_result]
            self.delegated_votes_result['election_counts'] += [question_delegation_result]

        self.result = result
        self.delegated_votes_frozen_at_date = self.voters_frozen_at_date =\
            self.result_tallied_at_date = datetime.datetime.now()

        # TODO: update result_hash
        self.save()

    def get_result_pretty(self):
        '''
        Returns self.result with total_count field. Format:

        #[
            #{
                #"a": "ballot/question",
                #"answers": [
                    #{
                        #"a": "ballot/answer",
                        #"value": "Alice",
                        #"total_count": 33,
                        #"by_direct_vote_count": 25,
                        #"by_delegation_count": 8,
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
        '''
        result_pretty = self.result
        i = 0
        for question in result_pretty:
            total_votes = 0
            for answer in question['answers']:
                answer['total_count'] = answer['by_direct_vote_count'] + answer['by_delegation_count']
                total_votes += answer['total_count']
            question['total_votes'] = total_votes
            for answer in question['answers']:
                if total_votes > 0:
                    answer['total_count_percentage'] = (answer['total_count'] * 100.0) / total_votes
                else:
                    answer['total_count_percentage'] = 0
        return result_pretty


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

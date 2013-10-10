import datetime
import uuid
import hashlib
import simplejson
import json

import markdown
import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.template.defaultfilters import truncatewords_html
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from guardian.shortcuts import *

from agora_site.misc.utils import JSONField, rest
from agora_site.agora_core.models.agora import Agora
from agora_site.agora_core.models.authority import Authority
from agora_site.agora_core.models.voting_systems.base import (
    parse_voting_methods, get_voting_system_by_id)
from agora_site.agora_core.templatetags.string_tags import urlify_markdown


class Election(models.Model):
    '''
    Represents an election.

    Recurrent elections are created as linked elections
    to a parent one. Parent election should always be the first in time in a group
    of recurrent/linked elections, i.e. the one with no parent election.

    The general succesion of statuses for an election:

    created
      \/
    approved
      \/
    frozen
      \/
    pubkey created
      \/
    started
      \/
    finished
      \/
    tallied
      \/
    tally released

    Some of those states are not required or may change positions. Additionally,
    the election could change to archived state at any time.
    '''

    # Prohibited because the urls would be a mess
    PROHIBITED_ELECTION_NAMES = ('new', 'delete', 'remove', 'election', 'admin', 'view', 'edit')

    SECURITY_POLICY = (
        ('PUBLIC_VOTING', _('Vote is public')),
        ('ALLOW_SECRET_VOTING', _('Allow secret voting')),
        ('ALLOW_ENCRYPTED_VOTING', _('Allow secret and encrypted voting')),
    )

    # cache the hash of the election. It will be null until frozen
    hash = models.CharField(max_length=100, unique=True, null=True)

    class Meta:
        app_label = 'agora_core'

    def task_id(self, task):
        return "election_task_" + str(self.id) + task.name

    def get_link(self):
        return self.url

    def get_vote_link(self):
        return self.url + "/vote"

    def delete(self, *args, **kwargs):
        '''
        Delete reimplemented to remove votes and actions related to the election
        '''
        from actstream.models import Action
        self.cast_votes.all().delete()
        Action.objects.object_actions(self).all().delete()
        super(Election, self).delete(*args, **kwargs)

    def get_serializable_data(self):
        data = {
            'creator_username': self.creator.username,
            'agora_name': self.agora.name,
            'url': self.url,
            'uuid': self.uuid,
            'security_policy': self.security_policy,
            'created_at_date': self.created_at_date.isoformat(),
            'is_vote_secret': self.is_vote_secret(),
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
        verbose_name=_('Electorate'), null=True, blank=True)

    parent_election = models.ForeignKey('self', related_name='children_elections',
        verbose_name=_('Parent Election'), default=None, null=True)

    created_at_date = models.DateTimeField(_(u'Created at date'))

    security_policy = models.CharField(max_length=50, choices=SECURITY_POLICY,
        default=SECURITY_POLICY[0][0])

    is_approved = models.BooleanField(_('Is Approved'), default=False)

    comments_policy = models.CharField(max_length=50, choices=Agora.COMMENTS_PERMS,
        default=Agora.COMMENTS_PERMS[0][0])

    last_modified_at_date = models.DateTimeField(_(u'Last Modified at Date'), auto_now_add=True, editable=True)

    voting_starts_at_date = models.DateTimeField(_(u'Voting Starts Date'), auto_now_add=False, default=None, blank=True, null=True)

    voting_ends_at_date = models.DateTimeField(_(u'Voting Ends Date'), auto_now_add=False, default=None, blank=True, null=True)

    voting_extended_until_date = models.DateTimeField(_(u'Voting Extended until Date'), auto_now_add=False, default=None, null=True)

    approved_at_date = models.DateTimeField(_(u'Approved at Date'), auto_now_add=False, default=None, null=True)

    frozen_at_date = models.DateTimeField(_(u'Frozen at Date'), auto_now_add=False, default=None, null=True)

    archived_at_date = models.DateTimeField(_(u'Archived at Date'), auto_now_add=False, default=None, null=True)

    delegated_votes_frozen_at_date = models.DateTimeField(_(u'Delegated Votes at Date'), auto_now_add=False, default=None, null=True)

    voters_frozen_at_date = models.DateTimeField(_(u'Voters Frozen at Date'), auto_now_add=False, default=None, null=True)

    result_tallied_at_date = models.DateTimeField(_(u'Result Tallied at Date'), auto_now_add=False, default=None, null=True)

    # this is automatically set if the election is not encrypted
    pubkey_created_at_date = models.DateTimeField(_(u'Public Key Created at Date'), auto_now_add=False, default=None, null=True)

    tally_released_at_date = models.DateTimeField(_(u'Talliy Released at Date'), auto_now_add=False, default=None, null=True)

    # contains the actual result in JSON format
    # something like:
    #{
        #'a':'result',
        #'delegation_counts':{
            #'2':1
        #},
        #'counts':[
            #{
                #'a':'question/result/ONE_CHOICE',
                #'winners': ['foo'],
                #'min':0,
                #'max':1,
                #'tally_type':'ONE_CHOICE',
                #'question':'Do you prefer foo or bar?',
                #'answers':[
                    #{
                        #'a':'answer/result/ONE_CHOICE',
                        #'by_delegation_count':2,
                        #'url':u'',
                        #'total_count':3,
                        #'by_direct_vote_count':1,
                        #'value':'foo',
                        #'details':u'',
                        #'total_count_percentage':60.0
                    #},
                    #{
                        #'a':'answer/result/ONE_CHOICE',
                        #'by_delegation_count':0,
                        #'url':u'',
                        #'total_count':2,
                        #'by_direct_vote_count':2,
                        #'value':'bar',
                        #'details':u'',
                        #'total_count_percentage':40.0
                    #},
                    #{
                        #'a':'answer/result/ONE_CHOICE',
                        #'by_delegation_count':0,
                        #'url':u'',
                        #'total_count':0,
                        #'by_direct_vote_count':0,
                        #'value':'none',
                        #'details':u'',
                        #'total_count_percentage':0.0
                    #}
                #],
                #'randomize_answer_order':True,
                #'total_votes':5
            #}
        #]
    #}
    result = JSONField(_('Election Result'), null=True)

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
            #"tally_type": "ONE_CHOICE"
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

    # stores delegation status data in the following format:
    # {
    #     'create_election__session_ids: ['id1', 'id2', ...],
    #     'create_election__status: 'success|requested|error requesting|error',
    #     'create_election__director_id': <id>,
    #     'tally_election__session_ids': ['id1', 'id2', ...],
    #     'tally_election__status: 'success|requested|error requesting|error',
    #     'tally_election__director_id': <id>,
    # }
    orchestra_status = JSONField(null=True)

    # Public keys
    # format: ['pubkey1', 'pubkey2', ...]
    pubkeys = JSONField(null=True)

    authorities = models.ManyToManyField(Authority, related_name='elections',
        verbose_name=_('Authorities'))

    def get_winning_option(self):
        '''
        Returns data of the winning option for the first question or throw an exception
        '''
        if not self.result:
            raise Exception('Election not tallied yet')
        elif len(self.result['counts']) == 0 or\
            not get_voting_system_by_id(self.result['counts'][0]['tally_type']):
            raise Exception('Unknown election result type: %s' % self.result['counts'][0]['tally_type'])

        winner = dict(value='', total_count=0.0, total_count_percentage=0.0)

        for answer in self.result['counts'][0]['answers']:
            if answer['value'] == self.result['counts'][0]['winners'][0]:
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
        return self.voting_starts_at_date != None and self.voting_starts_at_date < timezone.now()

    def has_ended(self):
        '''
        Returns true if voting has ended, false otherwise
        '''
        now = timezone.now()
        if self.voting_extended_until_date == None:
            return self.voting_ends_at_date and  self.voting_ends_at_date < timezone.now()
        else:
            return self.voting_extended_until_date and self.voting_extended_until_date < timezone.now()

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

    def is_tallied(self):
        '''
        Returns true if the election has been tallied, false otherwise
        '''
        return self.result_tallied_at_date != None

    def __has_perms(self, permission_name, user, isanon, isadmin,
            isadminorcreator, isarchived, isfrozen, ismember):
        '''
        Really implements has_perms function. It receives  by params usual
        has_perm args (permission_name, user) and also the arguments that are
        common in different has_perms checks, to make get_perms call more
        efficient.
        '''

        if permission_name == 'edit_details':
            return not self.has_started() and isadminorcreator and\
                not isarchived and not isfrozen
        elif permission_name == 'freeze_election':
            return not isfrozen and isadminorcreator and not isarchived
        elif permission_name == 'approve_election':
            return not self.is_approved and isadmin and not isarchived and\
                not self.has_started()
        elif permission_name == 'begin_election':
            pk_pass = not self.is_secure() or self.pubkey_created_at_date is not None
            return not self.voting_starts_at_date and isadmin and not isarchived and\
                self.is_approved and pk_pass
        elif permission_name == 'end_election':
            return self.has_started() and not self.voting_ends_at_date and\
                isadmin and not isarchived
        elif permission_name == 'archive_election':
            return isadminorcreator and not isarchived
        elif permission_name == 'comment':
            if self.comments_policy == Agora.COMMENTS_PERMS[0][0]:
                return not isarchived
            elif self.comments_policy == Agora.COMMENTS_PERMS[1][0]:
                return ismember() and not isarchived
            elif self.comments_policy == Agora.COMMENTS_PERMS[2][0]:
                return isadminorcreator and not isarchived
            else:
                return False
        elif permission_name == 'emit_direct_vote':
            canemit = ismember() or\
                (self.agora.has_perms('join', user) and self.agora.delegation_policy != Agora.DELEGATION_TYPE[1][0])
            return canemit and not isarchived and\
                isfrozen and self.has_started() and not self.has_ended()
        elif permission_name == 'vote_counts':
            return ismember() and not isarchived
        elif permission_name == 'emit_delegate_vote':
            can_emit = ismember() or\
                (self.agora.has_perms('join', user) and self.agora.delegation_policy != Agora.DELEGATION_TYPE[1][0])
            return can_emit and not isarchived and isfrozen and\
                self.has_started() and not self.has_ended()

    def has_perms(self, permission_name, user):
        '''
        Return whether a given user has a given permission name, depending on
        also in the state of the election.
        '''
        isanon = user.is_anonymous()
        if isanon:
            return False

        isadmin = self.agora.admins.filter(id=user.id).exists()
        isadminorcreator = (self.creator == user or isadmin)
        isarchived = self.is_archived()
        isfrozen = self.is_frozen()
        ismember = lambda: user in self.agora.members.all()
        return self.__has_perms(permission_name, user, isanon, isadmin,
            isadminorcreator, isarchived, isfrozen, ismember)

    def get_perms(self, user):
        '''
        Returns a list of permissions for a given user calling to self.has_perms()
        '''
        isanon = user.is_anonymous()
        if isanon:
            return False

        isadmin = self.agora.admins.filter(id=user.id).exists()
        isadminorcreator = (self.creator == user or isadmin)
        isarchived = self.is_archived()
        isfrozen = self.is_frozen()
        _ismember = user in self.agora.members.all()
        ismember = lambda: _ismember

        return [perm for perm in ('edit_details', 'approve_election',
            'begin_election', 'freeze_election', 'end_election',
            'archive_election', 'comment', 'emit_direct_vote',
            'emit_delegate_vote', 'vote_counts') if self.__has_perms(perm,
                user, isanon, isadmin, isadminorcreator, isarchived, isfrozen,
                ismember)]

    def ballot_is_open(self):
        '''
        Returns if the ballot is open, i.e. if one can vote. 
        TODO: In the future allow delegates to vote when election is frozen and
        voting hasn't started yet, so that others can delegate in them in
        advance. For now, any voter is a delegate.
        '''
        now = timezone.now()
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

        from agora_site.agora_core.models import CastVote

        # NOTE: When you have first voted directly in a voting and then you
        # delegate your vote in the agora, it's currently not counted. It makes
        # sense because you voted directly - cancel your direct vote if you
        # want your delegation to be active in that case
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
            #return self.cast_votes.filter(is_counted=True, invalidated_at_date=None)

    def get_delegated_votes(self):
        '''
        Delegated votes.

        NOTE that if your delegation is effective or not does
        not matter: even if your delegate didn't vote, your delegated vote will
        appear listed here when the election is running and has not been
        tallied.
        '''
        from agora_site.agora_core.models import CastVote
        if self.ballot_is_open():
            # valid direct votes
            q=self.cast_votes.filter(is_counted=True, is_direct=True,
                invalidated_at_date=None).values('voter__id').query

            return CastVote.objects.filter(
                # indirect votes from people who have an active delegation in
                # this agora:
                election=self.agora.delegation_election,
                is_direct=False, is_counted=True, invalidated_at_date=None

                # This is to avoid duplicates. If you voted directly, that's what
                # counts:
            ).exclude(is_direct=False, voter__id__in=q).order_by('-casted_at_date')
        else:
            return self.delegated_votes.all()


    def get_participation(self):
        '''
        Returns the participation details
        '''
        if self.is_tallied():
            total_votes = self.result['total_votes']

            if self.result['electorate_count'] > 0:
                percentage_of_participation = self.result['total_votes'] * 100.0 / self.result['electorate_count']
            else:
                percentage_of_participation = 0

            if self.result['total_votes'] > 0:
                percentage_of_delegation = self.result["total_delegated_votes"] * 100.0 / self.result['total_votes']
            else:
                percentage_of_delegation = 0

            return {
                'total_votes': self.result['total_votes'],
                'percentage_of_participation': percentage_of_participation,
                'total_delegated_votes': self.result["total_delegated_votes"],
                'percentage_of_delegation': percentage_of_delegation
            }
        else:
            if self.agora.members.count() != 0:
                percentage_of_direct_participation = self.get_direct_votes().count() * 100.0 / self.agora.members.count()
            else:
                percentage_of_direct_participation = 0
            return {
                'direct_votes': self.get_direct_votes().count(),
                'electorate_count': self.agora.members.count(),
                'percentage_of_direct_participation': percentage_of_direct_participation,
                'delegated_votes': self.get_delegated_votes().count()
            }

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

        if nodes.filter(voter=voter).count() == 1:
            return nodes.filter(voter=voter)[0]
        elif edges.filter(voter=voter).count() == 1:
            return edges.filter(voter=voter)[0]
        else:
            return None

    def is_vote_secret(self):
        '''
        Returns whether vote is secret for non-delegates/direct-votes
        '''
        return self.security_policy != Election.SECURITY_POLICY[0][0]

    def is_secure(self):
        '''
        Returns whether the vote is secret and encrypted
        '''
        return self.security_policy == Election.SECURITY_POLICY[2][0]

    def get_brief_description(self):
        '''
        Returns a brief description of the election
        '''
        desc = ''

        if self.agora.membership_policy == Agora.MEMBERSHIP_TYPE[0][0]:
            desc = _('This election allows everyone to vote. ')
            desc = desc.__unicode__()
        elif self.agora.membership_policy == Agora.MEMBERSHIP_TYPE[1][0]:
            desc = _('This election only allows agora members to vote, but any delegate can emit their position. ')
            desc = desc.__unicode__()
        elif self.agora.membership_policy == Agora.MEMBERSHIP_TYPE[2][0]:
            desc = _('This election only allows agora members to vote. ')
            desc = desc.__unicode__()

        if self.is_vote_secret():
            tmp = _('Vote is secret (public for delegates). ')
            desc += tmp.__unicode__()
        else:
            tmp = _('Vote is public. ')
            desc += tmp.__unicode__()
        now = timezone.now()

        def timesince(dati):
            return ('<time class="timeago" data-livestamp="%(isotime)s" '
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

    def request_pubkeys(self):
        '''
        Request the creation of the election to election authorities, in case of
        secure encrypted elections, which returns the pubkeys.

        Note: it assumes the permissions have been checked already.
        '''
        from agora_site.agora_core.tasks.election import create_pubkeys
        kwargs = dict(
            election_id=self.id
        )
        create_pubkeys.apply_async(kwargs=kwargs, task_id=self.task_id(create_pubkeys))

    def request_tally(self):
        '''
        Request the tally of the encrypted votes.
        '''
        pass

    def compute_result(self):
        '''
        Computes the result of the election
        '''
        from agora_site.agora_core.models import CastVote

        # Query with the direct votes in this election
        q=self.cast_votes.filter(
            is_counted=True,
            invalidated_at_date=None
        ).values('voter__id').query

        # Query with the delegated votes
        if self.agora.delegation_policy != Agora.DELEGATION_TYPE[1][0]:
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
        nodes = self.cast_votes.filter(is_direct=True,
            #is_counted=True, FIXME
            invalidated_at_date=None)

        # These are all the delegation votes, i.e. those that point to a delegate
        #edges = self.agora.delegation_election.cast_votes.filter(
            #is_direct=False, invalidated_at_date=None)
        edges = self.delegated_votes

        # list of saved paths. A path represent a list of users who delegate
        # into a given vote.
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

        # A dictionary where the number of delegated voted per delegate is
        # stored. This dict is used only for recording the number of delegated
        # votes a delegate has.
        #
        # The keys are the user_ids of the delegates, and the values are
        # the number of delegated votes.
        # Note that because of chains of delegations, the same vote can be
        # counted multiple times.
        delegation_counts = dict()

        def update_delegation_counts(vote):
            '''
            function used to update the delegation counts, for each valid vote.
            it basically goes deep in the delegation chain, updating the count
            for each delegate.

            NOTE: Calling to this function assumes a valid path for the vote,
            which means for example that the delegation chain is public.
            '''
            # if there is no vote we have nothing to do
            if not vote:
                return

            def increment_delegate(delegate_id):
                '''
                Increments the delegate count or sets it to one if doesn't it
                exist
                '''
                if delegate_id in delegation_counts:
                    delegation_counts[delegate_id] += 1
                else:
                    delegation_counts[delegate_id] = 1

            i = 0
            while not vote.is_direct:
                i += 1
                next_delegate = vote.get_delegate()
                if nodes.filter(voter=next_delegate).count() == 1:
                    increment_delegate(next_delegate.id)
                    return
                elif edges.filter(voter=next_delegate).count() == 1:
                    increment_delegate(next_delegate.id)
                    vote = edges.filter(voter=next_delegate)[0]
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

        def get_vote_for_voter(voter_id):
            '''
            Given a voter (an User), returns the vote of the vote of this voter
            on the election. It will be either a proxy or a direct vote
            '''
            if nodes.filter(voter_id=voter_id).count() == 1:
                return nodes.filter(voter_id=voter_id)[0]
            elif edges.filter(voter_id=voter_id).count() == 1:
                return edges.filter(voter_id=voter_id)[0]
            else:
                return None

        if self.election_type not in dict(parse_voting_methods()):
            raise Exception('do not know how to count this type of voting')

        voting_systems = []
        tallies = []

        import copy
        # result is in the same format as get_result_pretty(). Initialized here
        result = copy.deepcopy(self.questions)

        # setup the initial data common to all voting system
        i = 0
        for question in result:
            tally_type = self.election_type
            if 'tally_type' in question:
                tally_type = question['tally_type']
            voting_system = get_voting_system_by_id(tally_type)
            tally = voting_system.create_tally(self, i)
            voting_systems.append(voting_system)
            tallies.append(tally)
            i += 1

            question['a'] = "question/result/" + voting_system.get_id()
            question['winners'] = []
            question['total_votes'] = 0

            for answer in question['answers']:
                answer['a'] = "answer/result/" + voting_system.get_id()
                answer['total_count'] = 0
                answer['total_count_percentage'] = 0

            # prepare the tally
            tally.pre_tally(result)

        num_delegated_votes = 0
        def add_vote(user_answers, is_delegated):
            '''
            Given the answers of a vote, update the result
            '''
            for tally in tallies:
                tally.add_vote(voter_answers=user_answers, result=result,
                    is_delegated=is_delegated)

        # Here we go! for each voter, we try to find it in the paths, or in
        # the proxy vote chain, or in the direct votes pool
        for voter in self.electorate.all():
            path_for_user = get_path_for_user(voter.id)

            # Found the user in a known path
            if path_for_user and not path_for_user['is_broken_loop']:
                # found a path to which the user belongs

                # update delegation counts
                num_delegated_votes += 1
                add_vote(path_for_user['answers'], is_delegated=True)
                update_delegation_counts(get_vote_for_voter(voter.id))

            # found the user in a direct vote
            elif nodes.filter(voter=voter).count() == 1:
                vote = nodes.filter(voter=voter)[0]
                add_vote(vote.data["answers"], is_delegated=False)

            # found the user in an edge (delegated vote), but not yet in a path
            elif edges.filter(voter=voter).count() == 1:
                path = dict(
                    user_ids=[voter.id],
                    answers=[],
                    is_broken_loop=False
                )

                current_edge = edges.filter(voter=voter)[0]
                loop = True
                i = 0
                while loop:
                    i += 1
                    delegate = current_edge.get_delegate()
                    path_for_user = get_path_for_user(delegate.id)

                    if delegate.id in path['user_ids']:
                        # wrong path! loop found, vote won't be counted
                        path['is_broken_loop'] = True
                        paths += [path]
                        loop = False
                    elif path_for_user and not path_for_user['is_broken_loop']:
                        # extend the found path and count a new vote
                        path_for_user['user_ids'] += path['user_ids']

                        # Count the vote
                        num_delegated_votes += 1
                        add_vote(path_for_user['answers'], is_delegated=True)
                        update_delegation_counts(get_vote_for_voter(voter.id))
                        loop = False
                    elif nodes.filter(voter=delegate).count() == 1:
                        # The delegate voted directly
                        vote = nodes.filter(voter=delegate)[0]

                        # if the vote of the delegate is not public, then
                        # it doesn't count, we have finished
                        if not vote.is_public:
                            # wrong path! loop found, vote won't be counted
                            path['is_broken_loop'] = True
                            paths += [path]
                            loop = False
                            break

                        # add the path and count the vote
                        path["answers"] = vote.data['answers']
                        paths += [path]
                        num_delegated_votes += 1
                        add_vote(vote.data['answers'], is_delegated=True)
                        update_delegation_counts(get_vote_for_voter(voter.id))
                        loop = False

                    elif edges.filter(voter=delegate).count() == 1:
                        # the delegate also delegated
                        vote = edges.filter(voter=delegate)[0]

                        # if the vote of the delegate is not public, then
                        # it doesn't count, we have finished
                        if not vote.is_public:
                            # wrong path! loop found, vote won't be counted
                            path['is_broken_loop'] = True
                            paths += [path]
                            loop = False
                            break

                        # vote is public, so continue looping
                        path['user_ids'] += [delegate.id]
                        current_edge = vote
                    else:
                        # broken path! we cannot continue
                        path['is_broken_loop'] = True
                        paths += [path]
                        loop = False

        if not self.extra_data:
            self.extra_data = dict()

        # post process the tally
        for tally in tallies:
            tally.post_tally(result)

        self.result = dict(
            a= "result",
            counts = result,
            total_votes = result[0]['total_votes'] + result[0]['dirty_votes'],
            electorate_count = self.electorate.count(),
            total_delegated_votes = num_delegated_votes
        )

        tally_log = []
        for tally in tallies:
            tally_log.append(tally.get_log())
        self.extra_data['tally_log'] = tally_log

        def rank_delegate(delegate_count, delegation_counts):
            if delegate_count == 0:
                return None
            count = 0
            for key, value in delegation_counts.iteritems():
                if delegate_count <= value:
                    count += 1
            return count

        # refresh DelegateElectionCount items
        from agora_site.agora_core.models.delegateelectioncount import DelegateElectionCount
        DelegateElectionCount.objects.filter(election=self).delete()
        for key, value in delegation_counts.iteritems():
            dec = DelegateElectionCount(election=self, count=value)
            dec.rank = rank_delegate(value, delegation_counts)
            dec.count_percentage = value * 100.0 / self.result['total_votes']
            dec.delegate_vote = get_vote_for_voter(int(key))
            dec.delegate_id = int(key)
            dec.save()

        self.delegated_votes_frozen_at_date = self.voters_frozen_at_date =\
            self.result_tallied_at_date = timezone.now()

        # TODO: update result_hash
        self.save()

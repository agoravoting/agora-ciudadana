import datetime
import uuid
import json
from random import choice

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.db.models.signals import post_save
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from guardian.shortcuts import *
import requests

from agora_site.misc.utils import JSONField, get_users_with_perm
from agora_site.agora_core.models.voting_systems.base import parse_voting_methods

class Agora(models.Model):
    '''
    Represents an Agora, formed by a group of people which can vote and delegate
    '''
    ELECTION_TYPES = (
        ('SIMPLE_DELEGATION', _('Simple election for delegates where only one delegate can be chosen')),
    ) + parse_voting_methods()

    MEMBERSHIP_TYPE = (
        ('ANYONE_CAN_JOIN', _('Anyone can join')),
        ('JOINING_REQUIRES_ADMINS_APPROVAL_ANY_DELEGATE', _('Joining requires admins approval, allow non-member delegates')),
        ('JOINING_REQUIRES_ADMINS_APPROVAL', _('Joining requires admins approval and delegates must be agora members')),
        #('INVITATION_ONLY', _('Invitation only by admins')),
        #('EXTERNAL', _('External url')),
    )

    COMMENTS_PERMS = (
        ('ANYONE_CAN_COMMENT', _('Anyone can comment')),
        ('ONLY_MEMBERS_CAN_COMMENT', _('Only members can comment')),
        ('ONLY_ADMINS_CAN_COMMENT', _('Only admins can comment')),
        ('NO_COMMENTS', _('No comments')),
    )

    DELEGATION_TYPE = (
        ('ALLOW_DELEGATION', _('Allow delegation, delegation is public')),
        ('DISALLOW_DELEGATION', _('Disallow delegation')),
        ('ALLOW_SECRET_DELEGATION', _('Allow delegation, delegation can be secret')),
        ('ALLOW_ENCRYPTED_DELEGATION', _('Allow delegation, delegation can be secret and encrypted')),
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

    url = models.URLField(_('Url'))

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

    # stores delegation status data in the following format:
    # {
    #     'election_id': "",
    #     'created_at': "",
    #     'updated_at': "",
    #     'status': "",
    #     'pubkey': "",
    #     'director_id': 2,
    # }
    delegation_status = JSONField(null=True)

    def delete(self, *args, **kwargs):
        '''
        Delete reimplemented to remove elections and actions related to the agora
        '''
        from actstream.models import Action
        self.delegation_election.delete()
        self.elections.all().delete()
        Action.objects.object_actions(self).all().delete()
        super(Agora, self).delete(*args, **kwargs)

    def get_mugshot_url(self):
        '''
        Either returns image_url or a default image
        '''
        if self.image_url:
            return self.image_url
        else:
            return settings.STATIC_URL + 'img/agora_default_logo.png'

    def get_featured_election(self):
        '''
        Returns the feature election
        '''
        if not self.featured_election:
            return None
        else:
            try:
                return self.elections.filter(is_approved=True,
                    archived_at_date__isnull=True).order_by('-id')[0]
            except IndexError:
                return None

    def get_open_elections(self):
        '''
        Returns the list of current and future elections that will or are
        taking place.
        '''
        return self.elections.filter(
            Q(voting_extended_until_date__gt=timezone.now()) |
                Q(voting_extended_until_date=None,
                    voting_starts_at_date__lt=timezone.now()),
            Q(is_approved=True,
                archived_at_date__isnull=True)).order_by(
                    '-voting_extended_until_date',
                    '-voting_starts_at_date')

    def get_open_elections_with_name_start(self, name):
        '''
        Returns the list of current and future elections that will or are
        taking place, that start with a name.

        Used by ajax endpoint searchElection
        '''
        return self.elections.filter(
            Q(voting_extended_until_date__gt=timezone.now()) |
                Q(voting_extended_until_date=None,
                    voting_starts_at_date__lt=timezone.now()),
            Q(is_approved=True, archived_at_date__isnull=True),
            Q(pretty_name__icontains=name)).order_by('-voting_extended_until_date',
                '-voting_starts_at_date')

    def get_tallied_elections(self):
        '''
        Returns the list of past elections with a given result
        '''
        return self.elections.filter(
            tally_released_at_date__lt=timezone.now(),
            archived_at_date__isnull=True).order_by(
                '-tally_released_at_date')

    # Stablishes a default option for elections
    is_vote_secret = models.BooleanField(_('Is delegation secret'), default=False,
        help_text=_('if activated, when you delegate to someone, nobody will know who you delegated to'))

    # Stablishes a default option for elections
    #use_voter_aliases = models.BooleanField(_('Use Voter Aliases'), default=False)

    # Stablishes a default option for elections
    election_type = models.CharField(max_length=50, choices=ELECTION_TYPES,
        default=ELECTION_TYPES[0][0])

    featured_election = models.BooleanField(_('Is feature'), default=False)

    # Stablishes a default option for elections
    # eligibility is a JSON field, which lists auth_systems and eligibility details for that auth_system, e.g.
    # [{'auth_system': 'cas', 'constraint': [{'year': 'u12'}, {'year':'u13'}]}, {'auth_system' : 'password'}, {'auth_system' : 'openid',  'constraint': [{'host':'http://myopenid.com'}]}]
    eligibility = JSONField(null=True)

    membership_policy = models.CharField(max_length=50, choices=MEMBERSHIP_TYPE,
        default=MEMBERSHIP_TYPE[0][0])

    comments_policy = models.CharField(max_length=50, choices=COMMENTS_PERMS,
        default=COMMENTS_PERMS[0][0])

    delegation_policy = models.CharField(max_length=50, choices=DELEGATION_TYPE,
        default=DELEGATION_TYPE[0][0])

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
            ('denied_requested_membership', _('Denied requested membership')),
            ('invited_to_membership', _('Invited to membership')),
            ('requested_admin_membership', _('Requested admin membership')),
        )
        app_label = 'agora_core'

    def active_delegates(self):
        '''
        Returns active delegates of this agora: users that have emitted any valid
        and public vote in any election of this agora.
        '''

        from agora_site.agora_core.models import CastVote

        return User.objects.filter(
            id__in=CastVote.objects.filter(is_counted=True, is_direct=True, is_public=True,
                invalidated_at_date=None, election__agora__id=self.id).values('voter').query)

    def non_voters(self):
        '''
        Members who didn't vote
        '''
        from agora_site.agora_core.models import CastVote

        election = self.get_featured_election()
        return self.members.exclude(id__in=CastVote.objects.filter(is_counted=True, election__id=election.id).values('voter').query)

    def non_delegates(self):
        '''
        This will return those users not included by active_delegates()
        '''
        from agora_site.agora_core.models import CastVote

        return User.objects.exclude(
            id__in=CastVote.objects.filter(is_counted=True, is_direct=True, is_public=True,
                invalidated_at_date=None, election__agora__id=self.id).values('voter').query)

    def active_nonmembers_delegates(self):
        '''
        Same as active_delegates but all of those who are not currently a member
        of the agora.
        '''

        from agora_site.agora_core.models import CastVote

        return User.objects.filter(
            id__in=CastVote.objects.filter(is_counted=True, is_direct=True, is_public=True,
                invalidated_at_date=None, election__agora__id=self.id).values('voter').query
            )\
            .exclude(id__in=self.members.values('id').query)

    def users_who_requested_membership(self):
        '''
        Returns those users who requested membership in this Agora
        '''
        return get_users_with_perm(self, 'requested_membership')

    def users_with_denied_request_membership(self):
        '''
        Returns those users who requested membership in this Agora and were denied
        '''
        return get_users_with_perm(self, 'denied_requested_membership')

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
        return self.elections.filter(is_approved=True, archived_at_date__isnull=True)

    def open_elections(self):
        '''
        Returns the QuerySet with the open and approved elections
        '''

        return self.elections.filter(
            Q(voting_extended_until_date__gt=timezone.now()) |
            Q(voting_extended_until_date=None, voting_starts_at_date__lt=timezone.now()),
            Q(is_approved=True, archived_at_date__isnull=True)
        ).order_by('-voting_extended_until_date',
            '-voting_starts_at_date')


    def requested_elections(self):
        '''
        Returns a QuerySet with the not approved elections
        '''
        return self.elections.filter(is_approved=False, archived_at_date__isnull=True).exclude(name='delegation')

    @staticmethod
    def static_has_perms(permission_name, user):
        if permission_name == 'create':
            if settings.AGORA_CREATION_PERMISSIONS == 'any-user':
                return not user.is_anonymous()
            elif settings.AGORA_CREATION_PERMISSIONS == 'superusers-only':
                return user.is_superuser
            else:
                return False
        else:
            return False

    def is_archived(self):
        '''
        Returns true if the election has been archived, false otherwise
        '''
        return self.archived_at_date != None

    def __has_perms(self, permission_name, user, isanon, opc_perms, is_member,
            is_admin, isarchived, requires_membership_approval):
        '''
        Really implements has_perms. It receives  by params usual has_perm args
        (permission_name, user) and also thearguments that are common in different
        (has_perms checks, to make get_perms calls more efficient.
        '''
        if isarchived or isanon:
            return False

        if permission_name == 'join':
            return self.membership_policy == Agora.MEMBERSHIP_TYPE[0][0] and\
                not is_member()

        elif permission_name == 'request_membership':
            return requires_membership_approval and\
                not is_member() and not isarchived and\
                'requested_membership' not in opc_perms and\
                'denied_requested_membership' not in opc_perms

        elif permission_name == "cancel_membership_request":
            return requires_membership_approval and not is_member() and\
                ('requested_membership' in opc_perms or
                'denied_requested_membership' in opc_perms)

        elif permission_name == 'request_admin_membership':
            return is_member() and not is_admin() and\
                'requested_admin_membership' not in opc_perms

        elif permission_name == "cancel_admin_membership_request":
            return is_member() and not is_admin() and\
                'requested_admin_membership' in opc_perms

        elif permission_name == 'leave':
            return self.creator != user and is_member() and\
                not is_admin()

        elif permission_name == 'admin':
            return self.creator == user or is_admin()

        elif permission_name == 'leave_admin':
            return self.creator != user and is_admin()

        # NOTE: this is similar to asking "does this userhave an email and is
        # a member of this agora?". But it's not same as "does this user have
        # 'receive_mail' permission from XX user, because we have not been given
        # the second user. This second condition is only true if the first
        # question is true and the second user is an admin of this agora.
        elif permission_name == 'receive_mail':
            try:
                validate_email(user.email)
            except ValidationError:
                return False
            return is_member() or self.__has_perms("cancel_membership_request",
                user, isanon, opc_perms, is_member, is_admin, isarchived, requires_membership_approval) or\
                ('denied_requested_membership' in opc_perms)

        elif permission_name == 'comment':
            if self.comments_policy == Agora.COMMENTS_PERMS[0][0]:
                return True
            elif self.comments_policy == Agora.COMMENTS_PERMS[1][0]:
                return is_member()
            elif self.comments_policy == Agora.COMMENTS_PERMS[2][0]:
                return is_admin()
            else:
                return False

        elif permission_name == 'delete':
            return self.creator == user

        # any user can request to create an election, for now
        elif permission_name == 'create_election':
            return True

        elif permission_name == 'delegate':
            allow = is_member() and self.delegation_policy != Agora.DELEGATION_TYPE[1][0]
            if not allow:
                return False

            # if encrypted, we need a pubkey
            if self.delegation_policy == Agora.DELEGATION_TYPE[3][0]:
                return isinstance(self.delegation_status, dict) and\
                    self.delegation_status.get('status', None) == 'success'

            return True

        elif permission_name == 'cancel_vote_delegation':
            return is_member() and\
                self.delegation_election.cast_votes.filter(
                    is_direct=False, invalidated_at_date=None,
                    voter=user).exists()

    def has_perms(self, permission_name, user):
        '''
        Return whether a given user has a given permission name, depending on
        also in the state of the election.
        '''

        isanon = user.is_anonymous()

        is_superuser = user.is_superuser
        user.is_superuser = False
        is_member = lambda: not isanon and self.members.filter(id=user.id).exists()
        is_admin = lambda: not isanon and self.admins.filter(id=user.id).exists()

        opc_perms = None
        if not isanon:
            opc = ObjectPermissionChecker(user)
            opc_perms = opc.get_perms(self)
        user.is_superuser = is_superuser

        isarchived = self.is_archived()

        requires_membership_approval = (
            self.membership_policy == Agora.MEMBERSHIP_TYPE[1][0] or\
            self.membership_policy == Agora.MEMBERSHIP_TYPE[2][0]
        )

        return self.__has_perms(permission_name, user, isanon, opc_perms,
            is_member, is_admin, isarchived, requires_membership_approval)

    def get_perms(self, user):
        '''
        Returns a list of permissions for a given user calling to self.has_perms()
        '''
        isanon = user.is_anonymous()

        is_superuser = user.is_superuser
        user.is_superuser = False

        _is_member = not isanon and self.members.filter(id=user.id).exists()
        is_member = lambda: _is_member

        _is_admin = not isanon and self.admins.filter(id=user.id).exists()
        is_admin = lambda: _is_admin

        opc_perms = None
        if not isanon:
            opc = ObjectPermissionChecker(user)
            opc_perms = opc.get_perms(self)

        user.is_superuser = is_superuser

        isarchived = self.is_archived()

        requires_membership_approval = (
            self.membership_policy == Agora.MEMBERSHIP_TYPE[1][0] or\
            self.membership_policy == Agora.MEMBERSHIP_TYPE[2][0]
        )

        return [perm for perm in ('join', 'request_membership', 'admin',
            'cancel_membership_request', 'request_admin_membership', 'delete',
            'cancel_admin_membership_request', 'leave', 'leave_admin',
            'comment', 'create_election', 'delegate', 'cancel_vote_delegation',
            'receive_mail')
                if self.__has_perms(perm, user, isanon, opc_perms, is_member,
                    is_admin, isarchived, requires_membership_approval)]

    def get_delegated_vote_for_user(self, user):
        '''
        If the given user has delegated the vote, return this delegated vote
        '''
        votes = self.delegation_election.cast_votes.filter(is_direct=False,
            invalidated_at_date=None, voter__id=user.id)
        if votes.count() == 0:
            return None
        else:
            return votes[0]

    def get_link(self):
        return self.url

    def get_full_name(self, mode="plain"):
        '''
        Returns the name of the agora, for example "edulix/pdi-testing"

        mode can be:
         * "plain" : something like: edulix/pdi-testing
         * "link": something like: <a href="/edulix/pdi-testing">edulix / pdi-testing</a>
         * "link-agora": something like: edulix / <a href="/edulix/pdi-testing">pdi-testing</a>
         * "link-creator": something like: <a href="/user/edulix">edulix</a> / pdi-testing
        '''
        if mode == "plain":
            return self.creator.username + "/" + self.name
        elif mode == "link":
            return '<a href="%(url)s">%(username)s / %(agoraname)s</a>' % dict(
                url=self.get_link(), username=self.creator.username,
                agoraname=self.name
            )
        elif mode == "link-agora":
            return '%(username)s / <a href="%(url)s">%(agoraname)s</a>' % dict(
                url=self.get_link(), username=self.creator.username,
                agoraname=self.name
            )
        elif mode == "link-user":
            return '<a href="%(url)s">%(username)s</a> / %(agoraname)s' % dict(
                url=reverse('user-view', kwargs=dict(username=self.creator.username)),
                username=self.creator.username,
                agoraname=self.name
            )

    def request_new_delegation_election(self):
        '''
        Requests a new delegation election, with a new Session ID, to election
        authorities
        '''
        auths = self.agora_local_authorities.all()
        if len(auths) < settings.MIN_NUM_AUTHORITIES or\
                len(auths) > settings.MAX_NUM_AUTHORITIES:
            raise Exception("Invalid number of authorities")

        director = choice(auths)
        callback_url = '%s/api/v1/update/agora/%d/delegation_election/' %\
            (settings.AGORA_BASE_URL, self.id)

        now = datetime.datetime.utcnow().isoformat()
        payload = {
            "election_id": str(uuid.uuid4()),
            "is_recurring": True,
            "callback_url": callback_url,
            "extra": [],
            "title": self.name,
            "url": self.url,
            "description": self.short_description,
            "questions_data": [{
                "tally_type": "DELEGATION_ELECTION"
            }],
            "voting_start_date": now,
            # very long expiration date for delegation election
            "voting_end_date": "2050-12-06T18:17:14.457000",
            "authorities": [
                {
                    "name": auth.name,
                    "orchestra_url": auth.url,
                    "ssl_cert": auth.ssl_certificate
                } for auth in auths
            ]
        }

        r = requests.post(director.get_public_url('election'),
            data=json.dumps(payload), verify=False,
            cert=(settings.SSL_CERT_PATH,
                settings.SSL_KEY_PATH))

        pubkey = ""
        if r.status_code != 202:
            status = "error requesting"
            pubkey = r.text
        else:
            status = 'requested'

        self.delegation_status = {
            'election_id': payload["election_id"],
            'created_at': now,
            'updated_at': now,
            'status': status,
            'pubkey': pubkey,
            'director_id': director.id,
        }
        self.save()


def create_delegation_election(sender, instance, created, **kwargs):
    if not created:
        return

    from agora_site.agora_core.models import Election

    election = Election()
    election.agora = instance
    election.creator = instance.creator
    election.name = "delegation"
    # Delegation elections do not actually need an url
    election.url = "http://example.com/delegation/has/no/url/" + str(uuid.uuid4())
    election.description = election.short_description = "voting used for delegation"
    election.election_type = Agora.ELECTION_TYPES[1][0] # simple delegation
    election.uuid = str(uuid.uuid4())
    election.created_at_date = timezone.now()
    election.create_hash()
    election.save()

    instance.delegation_election = election
    instance.save()

post_save.connect(create_delegation_election, sender=Agora)

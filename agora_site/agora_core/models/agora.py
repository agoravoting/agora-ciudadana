import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from guardian.shortcuts import *

from agora_site.misc.utils import JSONField, get_users_with_perm


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

    COMMENTS_PERMS = (
        ('ANYONE_CAN_COMMENT', _('Anyone can comment')),
        ('ONLY_MEMBERS_CAN_COMMENT', _('Only members can comment')),
        ('ONLY_ADMINS_CAN_COMMENT', _('Only admins can comment')),
        ('NO_COMMENTS', _('No comments')),
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
    is_vote_secret = models.BooleanField(_('Is delegation secret'), default=False,
        help_text=_('if activated, when you delegate to someone, nobody will know who you delegated to'))

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

    comments_policy = models.CharField(max_length=50, choices=COMMENTS_PERMS,
        default=COMMENTS_PERMS[0][0])

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
        app_label = 'agora_core'

    def active_delegates(self):
        '''
        Returns the QuerySet with the active delegates
        '''

        from agora_site.agora_core.models import CastVote

        return User.objects.filter(
            id__in=CastVote.objects.filter(is_counted=True, is_direct=True,
                invalidated_at_date=None, election__agora__id=self.id).values('id').query)

    def active_nonmembers_delegates(self):
        '''
        Same as active_delegates but all of those who are not currently a member
        of the agora.
        '''

        from agora_site.agora_core.models import CastVote

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

    def has_perms(self, permission_name, user):
        '''
        Return whether a given user has a given permission name, depending on
        also in the state of the election.
        '''

        isanon = user.is_anonymous()
        if isanon:
            return False

        is_superuser = user.is_superuser
        user.is_superuser = False

        opc = ObjectPermissionChecker(user)
        opc_perms = opc.get_perms(self)
        user.is_superuser = is_superuser

        isarchived = self.is_archived()


        requires_membership_approval = (
            self.membership_policy == Agora.MEMBERSHIP_TYPE[1][0] or\
            self.membership_policy == Agora.MEMBERSHIP_TYPE[2][0]
        )

        if permission_name == 'join':
            return self.membership_policy == Agora.MEMBERSHIP_TYPE[0][0] and\
                not user in self.members.all() and not isarchived

        elif permission_name == 'request_membership':
            return requires_membership_approval and\
                not user in self.members.all() and not isarchived and\
                'requested_membership' not in opc_perms

        elif permission_name == "cancel_membership_request":
            return requires_membership_approval and not user in self.members.all() and\
                'requested_membership' in opc_perms

        elif permission_name == 'request_admin_membership':
            return user in self.members.all() and user not in self.admins.all() and\
                'requested_admin_membership' not in opc_perms and\
                not isarchived

        elif permission_name == "cancel_admin_membership_request":
            return user in self.members.all() and user not in self.admins.all() and\
                'requested_admin_membership' in opc_perms

        elif permission_name == 'leave':
            return self.creator != user and user in self.members.all() and\
                user not in self.admins.all()

        elif permission_name == 'admin':
            return self.creator == user or user in self.admins.all() and\
                not isarchived

        elif permission_name == 'leave_admin':
            return self.creator != user and user in self.admins.all()

        elif permission_name == 'comment':
            if self.comments_policy == Agora.COMMENTS_PERMS[0][0]:
                return not isarchived
            elif self.comments_policy == Agora.COMMENTS_PERMS[1][0]:
                return user in self.members.all() and not isarchived
            elif self.comments_policy == Agora.COMMENTS_PERMS[2][0]:
                return user in self.admins.all() and not isarchived
            else:
                return False

        elif permission_name == 'delete':
            return self.creator == user

    def get_perms(self, user):
        '''
        Returns a list of permissions for a given user calling to self.has_perms()
        '''
        return [perm for perm in ('join', 'request_membership',
            'cancel_membership_request', 'request_admin_membership',
            'cancel_admin_membership_request', 'leave', 'leave_admin',
            'admin', 'comment') if self.has_perms(perm, user)]

    def get_link(self):
        return reverse('agora-view', kwargs=dict(username=self.creator.username,
            agoraname=self.name))

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
        elif mode == "link":
            return '<a href="%(url)s">%(username)s</a> / %(agoraname)s' % dict(
                url=reverse('user-view', kwargs=dict(username=self.creator.username)),
                username=self.creator.username,
                agoraname=self.name
            )

import datetime

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save

from userena.models import UserenaLanguageBaseProfile
from guardian.shortcuts import *

from agora_site.misc.utils import JSONField
from agora import Agora
from election import Election
from castvote import CastVote


class Profile(UserenaLanguageBaseProfile):
    '''
    Profile used together with django User class, and accessible via
    user.get_profile(), because  in settings we have configured:

    AUTH_PROFILE_MODULE = 'agora_site.agora_core.models.Profile'

    See https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-AUTH_PROFILE_MODULE
    for more details.
    '''
    user = models.OneToOneField(User)

    class Meta:
        app_label = 'agora_core'

    def get_fullname(self):
        '''
        Returns the full user name
        '''
        if self.user.last_name:
            return self.user.first_name + ' ' + self.user.last_name
        else:
            return self.user.first_name

    def get_short_description(self):
        '''
        Returns a short description of the user
        '''
        if self.short_description:
            return self.short_description
        else:
            return _('Is a member of %(num_agoras)d agoras and has emitted '
                ' %(num_votes)d direct votes.') % dict(
                    num_agoras=self.user.agoras.count(),
                    num_votes=self.count_direct_votes())

    def get_first_name_or_nick(self):
        if self.user.first_name:
            return self.user.first_name
        else:
            return self.user.username

    def has_perms(self, permission_name):
        '''
        Return whether a given user has a given permission name
        '''
        if permission_name == 'receive_email_updates':
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(self.user.email)
            except ValidationError:
                return False
            return self.email_updates
        else:
            return False

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

    def get_link(self):
        return reverse('user-view', kwargs=dict(username=self.user.username))


# definition of UserProfile from above
# ...

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)

from tastypie.models import create_api_key
post_save.connect(create_api_key, sender=User)


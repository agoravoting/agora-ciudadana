import hashlib
import simplejson

from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from guardian.shortcuts import *

from agora_site.misc.utils import JSONField
from agora_site.agora_core.models.election import Election
from agora_site.agora_core.models.castvote import CastVote


class DelegateElectionCount(models.Model):
    '''
    Stores how many people delegated into a delegate in a given election
    '''
    delegate = models.ForeignKey(User, related_name='delegate_election_counts',
        verbose_name=_('Delegate'), null=False)

    election = models.ForeignKey(Election, related_name='delegate_election_counts',
        verbose_name=_('Election'), null=False)

    # number of effective vote delegations
    count = models.IntegerField(null=False)

    # number of effective vote delegations / number of valid votes in the election
    # 0 if number of valid votes is zero
    count_percentage = models.FloatField(null=False, default=0)

    # position in the rank of delegates with more effective vote delegations
    # None if the delegate did not get any effective vote delegation
    rank = models.IntegerField(null=True, blank=True)

    created_at_date = models.DateTimeField(_(u'Created at date'),
        auto_now_add=True, editable=True, default=timezone.now())

    delegate_vote = models.ForeignKey(CastVote, related_name='delegate_election_count',
        verbose_name=_('Delegate vote'), null=True, blank=True, unique=True)

    class Meta:
        app_label = 'agora_core'
        unique_together = (('election', 'delegate'),)

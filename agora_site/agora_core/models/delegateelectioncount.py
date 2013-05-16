import hashlib
import simplejson

from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from guardian.shortcuts import *

from agora_site.misc.utils import JSONField
from agora_site.agora_core.models.election import Election


class DelegateElectionCount(models.Model):
    '''
    Stores how many people delegated into a delegate in a given election
    '''
    delegate = models.ForeignKey(User, related_name='delegate_election_counts',
        verbose_name=_('Delegate'), null=False)

    election = models.ForeignKey(Election, related_name='delegate_election_counts',
        verbose_name=_('election'), null=False)

    count = models.IntegerField(null=False)

    class Meta:
        app_label = 'agora_core'
        unique_together = (('election', 'delegate'),)

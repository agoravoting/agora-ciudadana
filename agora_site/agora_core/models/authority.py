# Copyright (C) 2013 Eduardo Robles Elvira <edulix AT wadobo DOT com>
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

import hashlib
from urlparse import urlparse

from django.db import models
from django.utils.translation import ugettext_lazy as _
from agora_site.agora_core.models.agora import Agora

class Authority(models.Model):
    '''
    Represent an election authority. Authorities can be created and modified
    by superusers through django-admin.
    '''
    name = models.CharField(_('Name'), max_length=255)

    url = models.CharField(_('URL'), max_length=255)

    public_url = models.CharField(_('Public URL'), max_length=255,
                                  null=True, blank=True)

    description = models.TextField(_('Description'), null=True, blank=True)

    ssl_certificate = models.TextField(_('SSL Certificate'))

    is_active = models.BooleanField(_('Is active'))

    agora = models.ForeignKey('Agora', related_name='agora_local_authorities',
        verbose_name=_('Related Agora'), null=True, blank=True, default=None)

    class Meta:
        app_label = 'agora_core'

    def get_public_url(self, action='election'):
        '''
        Returns the url of a public action.
        Currently existing actions are: election, tally.
        '''
        u = urlparse(self.url)
        return "https://%s/public_api/%s" % (u.netloc, action)

    def get_public_data(self, election_id, session_id, filename):
        '''
        Return the url of public data
        '''
        u = urlparse(self.url)
        return "https://%s/public_data/%s/%s/%s" % (u.netloc, election_id, session_id, filename)
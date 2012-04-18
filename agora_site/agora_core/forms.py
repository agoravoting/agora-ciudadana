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

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.conf import settings

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden, Layout, Fieldset
from agora_site.agora_core.models import Agora, Election

from django import forms as django_forms

class CreateAgoraForm(django_forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(CreateAgoraForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.request = request
        self.helper.layout = Layout(Fieldset(_('Create Agora'), 'pretty_name', 'short_description'))
        self.helper.add_input(Submit('submit', _('Create Agora'), css_class='btn btn-success btn-large'))

    def save(self, *args, **kwargs):
        agora = super(CreateAgoraForm, self).save(commit=False)
        agora.create_name(self.request.user)
        agora.creator = self.request.user

        agora.delegation_election = election = Election()
        election.creator = self.request.user
        election.name = "delegation"
        election.description = election.short_description = "voting used for delegation"
        election.election_type = Agora.ELECTION_TYPES[1][0] # simple delegation
        election.save()
        agora.save()
        agora.members.add(self.request.user)
        agora.admins.add(self.request.user)
        agora.save()
        return agora

    class Meta:
        model = Agora
        fields = ('pretty_name', 'short_description')
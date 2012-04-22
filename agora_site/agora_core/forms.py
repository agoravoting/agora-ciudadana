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

import uuid

from django import forms as django_forms
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden, Layout, Fieldset

from agora_site.agora_core.models import Agora, Election


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

class CreateElectionForm(django_forms.ModelForm):
    question = django_forms.CharField(_("Question"), required=True)
    answers = django_forms.CharField(_("Answers"), required=True,
        help_text=_("each choice on separate lines"), widget=django_forms.Textarea)

    def __init__(self, request, agora, *args, **kwargs):
        super(CreateElectionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.request = request
        self.agora = agora
        self.helper.layout = Layout(Fieldset(_('Create election'),
            'pretty_name', 'description', 'question', 'answers'))
        self.helper.add_input(Submit('submit', _('Create Election'),
            css_class='btn btn-success btn-large'))

    def save(self, *args, **kwargs):
        election = super(CreateElectionForm, self).save(commit=False)
        election.agora = self.agora
        election.create_name()
        election.uuid = uuid.uuid4()
        election.creator = self.request.user
        election.short_description = election.description[:140]
        election.url = self.request.build_absolute_uri(reverse('election-view',
            kwargs=dict(username=election.agora.creator.username, agoraname=election.agora.name,
                electionname=election.name)))
        election.election_type = Agora.ELECTION_TYPES[0][0] # ONE CHOICE
        election.is_vote_secret = False

        # Anyone can create a voting for a given agora, but if you're not the
        # admin, it must be approved
        if election.agora.creator in election.agora.admins.all():
            election.is_approved = True
        else:
            election.is_approved = False
            #TODO send notification to admins if agora is configured to do so

        # Questions/answers have a special formatting
        answers = []
        for answer_value in self.cleaned_data["answers"].splitlines():
            answers += {
                "a": "ballot/answer",
                "value": answer_value.strip(),
                "url": "",
                "details": "",
            }

        election.questions = [{
                "a": "ballot/question",
                "answers": answers,
                "max": 1, "min": 0,
                "question": self.cleaned_data["question"],
                "randomize_answer_order": True,
                "tally_type": "simple"
            },]
        election.save()

        return election

    class Meta:
        model = Election
        fields = ('pretty_name', 'description')
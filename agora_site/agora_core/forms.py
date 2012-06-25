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
import datetime
import random

from django import forms as django_forms
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.comments.forms import CommentSecurityForm
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden, Layout, Fieldset
from actstream.models import Action
from actstream.signals import action as actstream_action

from agora_site.agora_core.models import Agora, Election, CastVote

COMMENT_MAX_LENGTH = getattr(settings, 'COMMENT_MAX_LENGTH', 3000)

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
        agora.url = self.request.build_absolute_uri(reverse('agora-view',
            kwargs=dict(username=agora.creator.username, agoraname=agora.name)))

        election = Election()
        agora.save()
        election.agora = agora
        election.creator = self.request.user
        election.name = "delegation"
        # Delegation elections do not actually need an url
        election.url = "http://example.com/delegation/has/no/url/" + str(uuid.uuid4())
        election.description = election.short_description = "voting used for delegation"
        election.election_type = Agora.ELECTION_TYPES[1][0] # simple delegation
        election.uuid = str(uuid.uuid4())
        election.created_at_date = datetime.datetime.now()
        election.create_hash()
        election.save()
        agora.delegation_election = election
        agora.members.add(self.request.user)
        agora.admins.add(self.request.user)
        agora.save()
        return agora

    class Meta:
        model = Agora
        fields = ('pretty_name', 'short_description')


class AgoraAdminForm(django_forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(AgoraAdminForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.request = request
        self.helper.layout = Layout(Fieldset(_('General settings'), 'pretty_name', 'short_description', 'biography'))
        self.helper.add_input(Submit('submit', _('Save settings'), css_class='btn btn-success btn-large'))

    class Meta:
        model = Agora
        fields = ('pretty_name', 'short_description', 'biography')

class CreateElectionForm(django_forms.ModelForm):
    question = django_forms.CharField(_("Question"), required=True)
    answers = django_forms.CharField(_("Answers"), required=True,
        help_text=_("Each choice on separate lines"), widget=django_forms.Textarea)

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

    def clean_answers(self, *args, **kwargs):
        data = self.cleaned_data["answers"]

        answers = [answer_value.strip()
            for answer_value in self.cleaned_data["answers"].splitlines()
                if answer_value.strip()]

        if len(answers) < 2:
            raise forms.ValidationError(_('You need to provide at least two '
                'possible answers'))
        return data

    def save(self, *args, **kwargs):
        election = super(CreateElectionForm, self).save(commit=False)
        election.agora = self.agora
        election.create_name()
        election.uuid = str(uuid.uuid4())
        election.created_at_date = datetime.datetime.now()
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
            if answer_value.strip():
                answers += [{
                    "a": "ballot/answer",
                    "value": answer_value.strip(),
                    "url": "",
                    "details": "",
                }]

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

class VoteForm(django_forms.ModelForm):
    '''
    Given an election, creates a form that lets the user choose the options
    he want to vote
    '''
    def __init__(self, request, election, *args, **kwargs):
        super(VoteForm, self).__init__(*args, **kwargs)
        self.election = election
        self.helper = FormHelper()
        self.helper.form_action = reverse('election-vote',
            kwargs=dict(username=self.election.agora.creator.username,
                agoraname=self.election.agora.name, electionname=self.election.name))
        self.request = request

        i = 0
        for question in election.questions:
            answers = [(answer['value'], answer['value'])
                for answer in question['answers']]
            random.shuffle(answers)

            self.fields.insert(0, 'question%d' % i, django_forms.ChoiceField(
                label=question['question'], choices=answers, required=True,
                widget=django_forms.RadioSelect(attrs={'class': 'question'})))
            i += 1

        self.helper.add_input(Submit('submit', _('Vote'),
            css_class='btn btn-success btn-large'))

    def clean(self):
        cleaned_data = super(VoteForm, self).clean()

        if not self.election.ballot_is_open():
            raise forms.ValidationError("Sorry, you cannot vote in this election.")

        return cleaned_data

    def save(self, *args, **kwargs):
        # invalidate older votes from the same voter to the same election
        old_votes = self.election.cast_votes.filter(is_public=True,
            is_direct=True, invalidated_at_date=None, voter=self.request.user)
        for old_vote in old_votes:
            old_vote.invalidated_at_date = datetime.datetime.now()
            old_vote.is_counted = False
            old_vote.save()
        vote = super(VoteForm, self).save(commit=False)

        data = {
            "a": "vote",
            "answers": [],
            "election_hash": {"a": "hash/sha256/value", "value": self.election.hash},
            "election_uuid": self.election.uuid
        }
        i = 0
        for question in self.election.questions:
            data["answers"] += [{
                "a": "plaintext-answer",
                "choices": [self.cleaned_data['question%d' % i]],
            }]
            i += 1

        if self.request.user not in self.election.agora.members.all():
            if self.election.agora.has_perms('join', self.request.user):
                # Join agora if possible
                from agora_site.agora_core.views import AgoraActionJoinView
                AgoraActionJoinView().post(self.request,
                    self.election.agora.creator.username, self.election.agora.name)

        vote.voter = self.request.user
        vote.election = self.election
        vote.is_counted = self.request.user in self.election.agora.members.all()
        vote.is_direct = True
        vote.is_public = True
        vote.reason = self.cleaned_data['reason']
        vote.data = data
        vote.casted_at_date = datetime.datetime.now()
        vote.create_hash()

        actstream_action.send(self.request.user, verb='voted', action_object=self.election,
            target=self.election.agora)

        vote.action_id = Action.objects.filter(actor_object_id=self.request.user.id,
            verb='voted', action_object_object_id=self.election.id,
            target_object_id=self.election.agora.id).order_by('-timestamp').all()[0].id

        vote.save()
        return vote

    class Meta:
        model = CastVote
        fields = ('reason',)
        widgets = {
            'reason': django_forms.TextInput(
                attrs={
                    'placeholder': _('Explain your public position on '
                    'the vote if you want'),
                    'maxlength': 140
                })
        }

class PostCommentForm(CommentSecurityForm):
    comment = django_forms.CharField(label='', max_length=COMMENT_MAX_LENGTH,
        widget=django_forms.Textarea(
            attrs=dict(placeholder=_('Post a comment here...'))))

    def __init__(self, request, instance=None, files=None, save=None, *args, **kwargs):
        super(PostCommentForm, self).__init__(*args, **kwargs)
        self.request = request

        self.helper = FormHelper()
        self.helper.form_id = "post-comment"
        self.helper.form_class = "form-inline"
        self.helper.add_input(Submit('submit', _('Send'), css_class='btn btn-success btn-large'))

    def save(self):
        obj = self.get_comment_object()
        obj.save()
        return obj

    def get_comment_object(self):
        """
        Return a new (unsaved) comment object based on the information in this
        form. Assumes that the form is already validated and will throw a
        ValueError if not.

        Does not set any of the fields that would come from a Request object
        (i.e. ``user`` or ``ip_address``).
        """
        if not self.is_valid():
            raise ValueError("get_comment_object may only be called on valid forms")

        CommentModel = self.get_comment_model()
        new = CommentModel(**self.get_comment_create_data())
        new = self.check_for_duplicate_comment(new)

        return new

    def get_comment_model(self):
        """
        Get the comment model to create with this form. Subclasses in custom
        comment apps should override this, get_comment_create_data, and perhaps
        check_for_duplicate_comment to provide custom comment models.
        """
        return Comment

    def get_comment_create_data(self):
        return dict(
            content_type = ContentType.objects.get_for_model(self.target_object),
            object_pk    = force_unicode(self.target_object._get_pk_val()),
            user         = self.request.user,
            comment      = self.cleaned_data["comment"],
            submit_date  = datetime.datetime.now(),
            site_id      = settings.SITE_ID,
            is_public    = True,
            is_removed   = False,
        )

    def check_for_duplicate_comment(self, new):
        """
        Check that a submitted comment isn't a duplicate. This might be caused
        by someone posting a comment twice. If it is a dup, silently return the *previous* comment.
        """
        possible_duplicates = self.get_comment_model()._default_manager.using(
            self.target_object._state.db
        ).filter(
            content_type = new.content_type,
            object_pk = new.object_pk,
            user = new.user,
        )
        for old in possible_duplicates:
            if old.submit_date.date() == new.submit_date.date() and old.comment == new.comment:
                return old

        return new

    def clean_comment(self):
        """
        If COMMENTS_ALLOW_PROFANITIES is False, check that the comment doesn't
        contain anything in PROFANITIES_LIST.
        """

        if not self.request.user.is_authenticated():
            raise forms.ValidationError(ungettext("You must be authenticated to post a comment"))

        comment = self.cleaned_data["comment"]
        if settings.COMMENTS_ALLOW_PROFANITIES == False:
            bad_words = [w for w in settings.PROFANITIES_LIST if w in comment.lower()]
            if bad_words:
                plural = len(bad_words) > 1
                raise forms.ValidationError(ungettext(
                    "Watch your mouth! The word %s is not allowed here.",
                    "Watch your mouth! The words %s are not allowed here.", plural) % \
                    get_text_list(['"%s%s%s"' % (i[0], '-'*(len(i)-2), i[-1]) for i in bad_words], 'and'))

        # Check security information
        if self.security_errors():
            raise forms.ValidationError(ungettext(
                "The comment form failed security verification: %s" % \
                    escape(str(self.security_errors()))))
        return comment

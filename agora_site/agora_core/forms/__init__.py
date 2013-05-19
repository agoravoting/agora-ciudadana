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
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib.comments.forms import CommentSecurityForm
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.utils import simplejson as json
from django.utils import translation
from django.utils import timezone
from django.contrib.sites.models import Site
from django.db import transaction

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden, Layout, Fieldset
from actstream.models import Action
from actstream.actions import follow, unfollow, is_following
from actstream.signals import action as actstream_action
from userena.models import UserenaSignup
from userena import settings as userena_settings

from agora_site.agora_core.models import Agora, Election, CastVote
from agora_site.agora_core.tasks.election import (start_election, end_election,
    send_election_created_mails)
from agora_site.agora_core.models.voting_systems.base import (
    parse_voting_methods, get_voting_system_by_id)
from agora_site.misc.utils import *

from .comment import *

COMMENT_MAX_LENGTH = getattr(settings, 'COMMENT_MAX_LENGTH', 3000)

class CreateAgoraForm(django_forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(CreateAgoraForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.request = request
        self.helper.layout = Layout(Fieldset(_('Create Agora'), 'pretty_name', 'short_description', 'is_vote_secret'))
        self.helper.add_input(Submit('submit', _('Create Agora'), css_class='btn btn-success btn-large'))

    def save(self, *args, **kwargs):
        agora = super(CreateAgoraForm, self).save(commit=False)
        agora.create_name(self.request.user)
        agora.creator = self.request.user
        agora.url = self.request.build_absolute_uri(reverse('agora-view',
            kwargs=dict(username=agora.creator.username, agoraname=agora.name)))

        # we need to save before add members
        agora.save()

        agora.members.add(self.request.user)
        agora.admins.add(self.request.user)

        action.send(self.request.user, verb='created', action_object=agora,
            ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        follow(self.request.user, agora, actor_only=False, request=self.request)

        return agora

    class Meta:
        model = Agora
        fields = ('pretty_name', 'short_description', 'is_vote_secret')


attrs_dict = {'class': 'required'}

class UserSettingsForm(django_forms.ModelForm):
    avatar = django_forms.ImageField(_('Avatar'),
        help_text=_("Upload an image to use as avatar instead of gravatar service"))
    delete_avatar = django_forms.BooleanField(label=_("Remove this avatar"),
                                              required=False)

    short_description = django_forms.CharField(label=_('Short Description'),  max_length=140,
        help_text=_("Say something about yourself (140 chars max)"), required=False)

    biography = django_forms.CharField(_('Biography'),
        help_text=_("Tell us about you, use as much text as needed"),
        widget=django_forms.Textarea, required=False)

    email = django_forms.EmailField(widget=django_forms.TextInput(attrs=dict(attrs_dict,
        maxlength=75)), label=_(u"Email"), required=False)

    email_updates = django_forms.BooleanField(label=_("Receive email updates"), required=False)

    old_password = django_forms.CharField(widget=django_forms.PasswordInput(attrs=attrs_dict,
        render_value=False), label=_("Current password"),
        help_text=_("Provide your current password for security, required field"),
        required=True)

    password1 = django_forms.CharField(widget=django_forms.PasswordInput(attrs=attrs_dict,
        render_value=False),label=_("New password"), required=False,
        help_text=_("Specify your new password if you want to change it, or leave it blank"))

    password2 = django_forms.CharField(widget=django_forms.PasswordInput(attrs=attrs_dict,
        render_value=False), required=False, label=_("Repeat new password"))

    def __init__(self, request, *args, **kwargs):
        super(UserSettingsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.request = request
        self.user = kwargs['instance']
        self.fields['short_description'].initial = self.user.get_profile().short_description
        self.fields['biography'].initial = self.user.get_profile().biography
        self.fields['email'].initial = self.user.email
        self.fields['email_updates'].initial = self.user.get_profile().email_updates
        self.fields['avatar'].required = False

        # Users who login via twitter or other means do not have a password
        if self.user.password == '!':
            del self.fields['old_password']
            self.helper.layout = Layout(
                Fieldset(_('Profile'), 'avatar', 'delete_avatar',
                    'first_name', 'last_name',
                    'short_description', 'biography', 'email_updates'),
                Fieldset(_('Change email'), 'email'),
                Fieldset(_('Change password'), 'password1', 'password2')
            )
        else:
            self.helper.layout = Layout(
                Fieldset(_('Security'), 'old_password'),
                Fieldset(_('Profile'), 'avatar', 'delete_avatar',
                    'first_name', 'last_name',
                    'short_description', 'biography', 'email_updates'),
                Fieldset(_('Change email'), 'email'),
                Fieldset(_('Change password'), 'password1', 'password2')
            )
        self.helper.add_input(Submit('submit', _('Save settings'), css_class='btn btn-success btn-large'))

    def save(self, *args, **kwargs):
        old_email = self.user.email
        user = super(UserSettingsForm, self).save(commit=False)
        profile = user.get_profile()
        profile.short_description = self.cleaned_data['short_description']
        profile.biography = self.cleaned_data['biography']
        profile.email_updates = self.cleaned_data['email_updates']

        avatar = self.cleaned_data['avatar']
        if avatar:
            if profile.mugshot:
                profile.mugshot.delete()
            profile.mugshot = avatar
        if self.cleaned_data['delete_avatar']:
            profile.mugshot.delete()
            profile.mugshot = None

        user.email = self.cleaned_data['email']
        if len(self.cleaned_data['password1']) > 0:
            user.set_password(self.cleaned_data['password1'])
        profile.save()
        user.save()
        return user

    def clean_email(self):
        """ Validate that the email is not already registered with another user """
        if User.objects.filter(email__iexact=self.cleaned_data['email']).exclude(email__iexact=self.user.email):
            raise django_forms.ValidationError(_(u'This email is already in use. Please supply a different email.'))
        return self.cleaned_data['email']

    def clean_old_password(self):
        """ Validate that the email is not already registered with another user """
        if not self.user.check_password(self.cleaned_data['old_password']):
            raise django_forms.ValidationError(_(u'Invalid password.'))
        return self.cleaned_data['old_password']

    def clean(self):
        """
        Validates that the values entered into the two password fields match.
        Note that an error here will end up in ``non_field_errors()`` because
        it doesn't apply to a single field.

        """
        if 'password' in self.cleaned_data and 'password2' in self.cleaned_data and\
            self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise django_forms.ValidationError(_('The two password fields didn\'t match.'))

        return self.cleaned_data

    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class AgoraAdminForm(django_forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(AgoraAdminForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.request = request
        self.helper.layout = Layout(Fieldset(_('General settings'), 'pretty_name', 'short_description', 'biography', 'is_vote_secret', 'membership_policy', 'comments_policy'))
        self.helper.add_input(Submit('submit', _('Save settings'), css_class='btn btn-success btn-large'))

    class Meta:
        model = Agora
        fields = ('pretty_name', 'short_description', 'is_vote_secret',
            'biography', 'membership_policy', 'comments_policy')
        widgets = {
            'membership_policy': django_forms.RadioSelect,
            'comments_policy': django_forms.RadioSelect
        }

def election_questions_validator(questions):
    '''
    Validates a list of questions checking the voting method used, etc
    '''
    error = django_forms.ValidationError(_('Invalid questions format'))

    # we need at least one question
    if not isinstance(questions, list) or len(questions) < 1:
        raise error

    for question in questions:
        # check type
        if not isinstance(question, dict):
            raise error

        # check it contains the valid elements
        if not list_contains_all(['a', 'answers', 'max', 'min', 'question',
            'randomize_answer_order', 'tally_type'], question.keys()):
            raise error

        # let the voting system check the rest
        voting_system = get_voting_system_by_id(question['tally_type'])
        if not voting_system:
            raise error
        voting_system.validate_question(question)


class CreateElectionForm(django_forms.ModelForm):
    questions = JSONFormField(label=_('Questions'), required=True,
        validators=[election_questions_validator])

    from_date = ISODateTimeFormField(label=_('Start voting'), required=False,
        help_text=_("Not required, you can choose to start the voting period manually"))
    to_date = ISODateTimeFormField(label=_('End voting'), required=False,
        help_text=_("Not required, you can choose to end the voting period manually"))

    def __init__(self, request, agora, *args, **kwargs):
        super(CreateElectionForm, self).__init__(**kwargs)
        self.data = kwargs.get('data', dict())
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.request = request
        self.agora = agora
        self.fields['is_vote_secret'].initial = agora.is_vote_secret
        self.helper.layout = Layout(Fieldset(_('Create election'),
            'pretty_name', 'description', 'question', 'answers', 'is_vote_secret', 'from_date', 'to_date'))
        self.helper.add_input(Submit('submit', _('Create Election'),
            css_class='btn btn-success btn-large'))

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        agora = get_object_or_404(Agora, pk=kwargs["agoraid"])
        return dict(request=request, agora=agora, data=data)

    def clean(self, *args, **kwargs):
        cleaned_data = super(CreateElectionForm, self).clean()

        from_date = cleaned_data.get("from_date", None)
        to_date = cleaned_data.get("to_date", None)

        if not from_date and not to_date:
            return cleaned_data

        if (not from_date and to_date) or (from_date and not to_date):
            raise django_forms.ValidationError(_('You need to either provide '
                'none or both start and end voting dates'))

        if from_date < timezone.now():
            raise django_forms.ValidationError(_('Invalid start date, must be '
                'in the future'))

        if to_date - from_date < datetime.timedelta(hours=1):
            raise django_forms.ValidationError(_('Voting time must be at least 1 hour'))

        return cleaned_data

    def bundle_obj(self, obj, request):
        '''
        Bundles the object for the api
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        er = ElectionResource()
        bundle = er.build_bundle(obj=obj, request=request)
        bundle = er.full_dehydrate(bundle)
        return bundle

    def save(self, *args, **kwargs):
        election = super(CreateElectionForm, self).save(commit=False)
        election.agora = self.agora
        election.create_name()
        election.uuid = str(uuid.uuid4())
        election.created_at_date = timezone.now()
        election.creator = self.request.user
        election.short_description = election.description[:140]
        election.url = self.request.build_absolute_uri(reverse('election-view',
            kwargs=dict(username=election.agora.creator.username, agoraname=election.agora.name,
                electionname=election.name)))
        election.questions = self.cleaned_data['questions']
        election.election_type = election.questions[0]['tally_type']
        election.comments_policy = self.agora.comments_policy

        if ("from_date" in self.cleaned_data) and ("to_date" in self.cleaned_data):
            from_date = self.cleaned_data["from_date"]
            to_date = self.cleaned_data["to_date"]
            election.voting_starts_at_date = from_date
            election.voting_extended_until_date = election.voting_ends_at_date = to_date


        # Anyone can create a voting for a given agora, but if you're not the
        # admin, it must be approved
        if election.creator in election.agora.admins.all():
            election.is_approved = True
            election.approved_at_date = timezone.now()
        else:
            election.is_approved = False

        election.save()

        # create related action
        verb = 'created' if election.is_approved else 'proposed'
        actstream_action.send(self.request.user, verb=verb, action_object=election,
            target=election.agora, ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        # send email to admins
        context = get_base_email_context(self.request)
        context.update(dict(
            election=election,
            action_user_url='/%s' % election.creator.username,
        ))

        for admin in election.agora.admins.all():
            context['to'] = admin

            if not admin.has_perms('receive_email_updates'):
                continue

            translation.activate(admin.get_profile().lang_code)

            email = EmailMultiAlternatives(
                subject=_('Election %s created') % election.pretty_name,
                body=render_to_string('agora_core/emails/election_created.txt',
                    context),
                to=[admin.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/election_created.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        follow(self.request.user, election, actor_only=False, request=self.request)

        # used for tasks
        kwargs=dict(
            election_id=election.id,
            is_secure=self.request.is_secure(),
            site_id=Site.objects.get_current().id,
            remote_addr=self.request.META.get('REMOTE_ADDR'),
            user_id=self.request.user.id
        )

        # send email to admins
        send_election_created_mails.apply_async(kwargs=kwargs, task_id=election.task_id(send_election_created_mails))

        # schedule start and end of the election. note that if election is not
        # approved, the start and end of the election won't really happen
        if from_date and to_date:
            start_election.apply_async(kwargs=kwargs, task_id=election.task_id(start_election),
                eta=election.voting_starts_at_date)
            end_election.apply_async(kwargs=kwargs, task_id=election.task_id(end_election),
                eta=election.voting_ends_at_date)

        return election

    class Meta:
        model = Election
        fields = ('pretty_name', 'description', 'is_vote_secret')

class ElectionEditForm(django_forms.ModelForm):
    questions = JSONFormField(required=True, validators=[election_questions_validator])

    from_date = django_forms.DateTimeField(label=_('Start voting'), required=False,
        help_text=_("Not required, you can choose to start the voting period manually"),
        widget=django_forms.TextInput(attrs={'class': 'datetimepicker'}),
        input_formats=('%m/%d/%Y %H:%M',))
    to_date = django_forms.DateTimeField(label=_('End voting'), required=False,
        help_text=_("Not required, you can choose to end the voting period manually"),
        widget=django_forms.TextInput(attrs={'class': 'datetimepicker'}),
        input_formats=('%m/%d/%Y %H:%M',))

    def __init__(self, request, *args, **kwargs):
        super(ElectionEditForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.request = request

        instance = kwargs['instance']
        if instance.voting_starts_at_date and instance.voting_ends_at_date:
            self.fields['from_date'].initial = instance.voting_starts_at_date.strftime('%m/%d/%Y %H:%M')
            self.fields['to_date'].initial = instance.voting_ends_at_date.strftime('%m/%d/%Y %H:%M')

        self.helper.layout = Layout(Fieldset(_('General settings'), 'pretty_name', 'description', 'question', 'answers', 'is_vote_secret', 'comments_policy'))
        self.helper.add_input(Submit('submit', _('Save settings'), css_class='btn btn-success btn-large'))

    def clean(self, *args, **kwargs):
        cleaned_data = super(ElectionEditForm, self).clean()

        from_date = cleaned_data.get("from_date", None)
        to_date = cleaned_data.get("to_date", None)

        if not from_date and not to_date:
            return cleaned_data

        if (not from_date and to_date) or (from_date and not to_date):
            raise django_forms.ValidationError(_('You need to either provide '
                'none or both start and end voting dates'))

        if from_date < timezone.now():
            raise django_forms.ValidationError(_('Invalid start date, must be '
                'in the future'))

        if to_date - from_date < datetime.timedelta(hours=1):
            raise django_forms.ValidationError(_('Voting time must be at least 1 hour'))

        return cleaned_data

    def save(self, *args, **kwargs):
        election = super(ElectionEditForm, self).save(*args, **kwargs)

        election.questions = self.cleaned_data['questions']
        election.last_modified_at_date = timezone.now()

        # save so that in case a task is triggered, it has the correct questions
        # and last modified date
        election.save()

        if ("from_date" in self.cleaned_data) and ("to_date" in self.cleaned_data):
            from_date = self.cleaned_data["from_date"]
            to_date = self.cleaned_data["to_date"]
            election.voting_starts_at_date = from_date
            election.voting_extended_until_date = election.voting_ends_at_date = to_date
            election.save()
            transaction.commit()

            kwargs=dict(
                election_id=election.id,
                is_secure=self.request.is_secure(),
                site_id=Site.objects.get_current().id,
                remote_addr=self.request.META.get('REMOTE_ADDR'),
                user_id=self.request.user.id
            )
            start_election.apply_async(kwargs=kwargs, task_id=election.task_id(start_election),
                eta=election.voting_starts_at_date)
            end_election.apply_async(kwargs=kwargs, task_id=election.task_id(end_election),
                eta=election.voting_ends_at_date)

        return election

    class Meta:
        model = Election
        fields = ('pretty_name', 'description', 'is_vote_secret', 'comments_policy')
        widgets = {
            'comments_policy': django_forms.RadioSelect
        }


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

        if election.is_vote_secret:
            if self.request.user in self.election.agora.members.all() or\
                self.election.agora.has_perms('join', self.request.user):
                self.helper.add_input(Submit('submit-secret', _('Vote secretly'),
                    css_class='btn btn-success btn-large'))
                self.helper.add_input(Submit('submit', _('Vote in public as a delegate'),
                    css_class='btn btn-info btn-large separated-button'))
            else:
                self.helper.add_input(Submit('submit', _('Vote in public as a non-member delegate'),
                    css_class='btn btn-info btn-large'))
        else:
            if self.request.user in self.election.agora.members.all() or\
                self.election.agora.has_perms('join', self.request.user):
                self.helper.add_input(Submit('submit', _('Vote'),
                    css_class='btn btn-success btn-large'))
            else:
                self.helper.add_input(Submit('submit', _('Vote in public as a non-member delegate'),
                    css_class='btn btn-info btn-large'))

    def clean(self):
        cleaned_data = super(VoteForm, self).clean()

        if not self.election.ballot_is_open():
            raise django_forms.ValidationError("Sorry, you cannot vote in this election.")

        return cleaned_data

    def save(self, *args, **kwargs):
        # invalidate older votes from the same voter to the same election
        old_votes = self.election.cast_votes.filter(is_direct=True,
            invalidated_at_date=None, voter=self.request.user)
        for old_vote in old_votes:
            old_vote.invalidated_at_date = timezone.now()
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

        if self.election.is_vote_secret and ('submit-secret' in self.request.POST) and\
            (self.request.user in self.election.agora.members.all() or\
                self.election.agora.has_perms('join', self.request.user)):
            vote.is_public = False
            vote.reason = None
        else:
            vote.reason = self.cleaned_data['reason']
            vote.is_public = True
        vote.data = data
        vote.casted_at_date = timezone.now()
        vote.create_hash()

        actstream_action.send(self.request.user, verb='voted', action_object=self.election,
            target=self.election.agora,
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

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
                    'the vote if you want and if your vote is public'),
                    'maxlength': 140
                })
        }

class ContactForm(django_forms.Form):
    '''
    Contact form that can be used when the user is not logged in. Anyone
    can send it. Hence, we need information about the sender to be able to get
    back to it, and a captcha to avoid spammers.
    '''
    name = django_forms.CharField(label=_("Your name"), required=True,
        min_length=3, max_length=30)
    email = django_forms.EmailField(label=_(u"Your contact email"), required=True)
    subject = django_forms.CharField(label=_("Subject"), required=True,
        min_length=5, max_length=200)
    message = django_forms.CharField(label=_(u"Message"), required=True,
        min_length=5, max_length=1000, widget=django_forms.Textarea())

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.helper = FormHelper()
        if not request.user.is_authenticated():
            self.helper.layout = Layout(Fieldset(_('Contact'), 'name', 'email', 'subject', 'message'))
        else:
            self.helper.layout = Layout(Fieldset(_('Contact'), 'subject', 'message'))
        self.helper.add_input(Submit('submit', _('Send message'), css_class='btn btn-success btn-large'))
        super(ContactForm, self).__init__(*args, **kwargs)

    def send(self):
        subject = self.cleaned_data['subject']
        if self.request.user.is_authenticated():
            name = self.request.user.get_profile().get_fullname()
            email = self.request.user.email
        else:
            name = self.cleaned_data['name']
            email = self.cleaned_data['email']

        message = _("[%(site)s] Message from %(name)s <%(email)s>: \n\n %(msg)s") % dict(
            msg=self.cleaned_data['message'],
            email=email,
            site=Site.objects.get_current().name,
            name=name)

        from django.core.mail import mail_admins
        mail_admins(subject, message, email)
        messages.add_message(self.request, messages.SUCCESS,
            _("You have contacted us, we'll answer you as soon as possible."))

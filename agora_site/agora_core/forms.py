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
import re

from django import forms as django_forms
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives, EmailMessage, send_mass_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.comments.forms import CommentSecurityForm
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect, get_object_or_404, render_to_response
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.utils import simplejson as json
from django.contrib.sites.models import Site
from django.db import transaction

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden, Layout, Fieldset
from actstream.models import Action
from actstream.signals import action as actstream_action
from userena.models import UserenaSignup
from userena import settings as userena_settings

from agora_site.agora_core.models import Agora, Election, CastVote
from agora_site.agora_core.tasks import *
from agora_site.misc.utils import *

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
        fields = ('pretty_name', 'short_description', 'is_vote_secret')


attrs_dict = {'class': 'required'}

class UserSettingsForm(django_forms.ModelForm):
    avatar = django_forms.ImageField(_('Avatar'),
        help_text=_("Upload an image to use as avatar instead of gravatar service"))
    delete_avatar = django_forms.BooleanField(label=_("Remove this avatar"),
                                              required=False)

    short_description = django_forms.CharField(_('Short Description'),
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
                raise forms.ValidationError(_('The two password fields didn\'t match.'))

        return self.cleaned_data

    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class AgoraAddMembersForm(django_forms.ModelForm):
    new_members = django_forms.CharField(_("New members"), required=True,
        help_text=_("Each member must be in a new line. Format per line: "
            "&lt;existing_username&gt;|&lt;new_username&gt; &lt;email_address&gt;."),
            widget=django_forms.Textarea)
    welcome = django_forms.CharField(_("Welcome message"), required=True,
        help_text=_("Welcome message that these members will receive."),
            widget=django_forms.Textarea)

    def clean_new_members(self):
        """ Validate that the email is not already registered with another user """
        data = self.cleaned_data['new_members']
        agora = self.instance

        username_re = re.compile(r'^(?P<username>[\.\w]+)$')
        new_user_re = re.compile(r'^(?P<username>[\.\w]+) (?P<email>[^@]+@[^@]+\.[^@]+)$')


        self.adding_users = []
        self.new_users = []

        for line in data.splitlines():
            line = line.strip()
            match_username = username_re.match(line)
            match_new_user = new_user_re.match(line)

            if match_username:
                # it's only an existing username, try to add it

                # first check if the user exists
                username = line
                try:
                    user = get_object_or_404(User, username=username, is_active=True)
                except Exception, e:
                    raise django_forms.ValidationError(_(u'User %(username)s '
                        'does not exist.') % dict(username=username))

                # then check if the user is already a member
                if agora.members.filter(username=username).exists():
                    raise django_forms.ValidationError(_(u'User %(username)s '
                        'is already a member in this agora.')  %\
                            dict(username=username))

                self.adding_users += [user]

            elif match_new_user:
                new_username, email = match_new_user.groups()

                if User.objects.filter(username=new_username).exists():
                    raise django_forms.ValidationError(_(u'User %(username)s '
                        'already exists.') % dict(username=new_username))
                elif User.objects.filter(email=email).exists():
                    raise django_forms.ValidationError(_(u'User with email '
                        '%(email)s already exists.') % dict(email=email))

                self.new_users += [ (new_username, email) ]

        return self.cleaned_data['new_members']

    def save(self, *args, **kwargs):
        agora = self.instance

        # add existing users
        for user in self.adding_users:
            # adding to the agora
            agora.members.add(user)
            agora.save()

            # creating join action
            action.send(user, verb='joined', action_object=agora,
                ipaddr=self.request.META.get('REMOTE_ADDR'),
                geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

            # sending email
            if not user.email or not user.get_profile().email_updates:
                continue

            context = get_base_email_context(self.request)

            context.update(dict(
                agora=agora,
                to=user,
                other_user=self.request.user,
                notification_text=_('An administrator of the %(agora)s agora, %(user)s, has '
                    'added you to this agora. You can leave the agora at any time. If you '
                    'think this user is spamming you, please, contact us.\n\n') % dict(
                        agora=agora.get_full_name(),
                        user=self.request.user.username
                    ) + self.cleaned_data['welcome']
            ))
            email = EmailMultiAlternatives(
                subject=_('%(site)s - Added as member to %(agora)s') %\
                    dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        # adding new users
        for new_username, email in self.new_users:
            # creating user
            new_user = User(email=email, username=new_username, first_name=new_username)
            new_password = random_password()
            new_user.set_password(new_password)
            new_user.save()

            # creating join action
            action.send(new_user, verb='joined', action_object=agora,
                ipaddr=self.request.META.get('REMOTE_ADDR'),
                geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

            # adding the user to the agora
            agora.members.add(new_user)
            agora.save()

            # sending welcome email
            context = get_base_email_context(self.request)

            context.update(dict(
                agora=agora,
                to=new_user,
                other_user=self.request.user,
                notification_text=_('An administrator of the %(agora)s agora, %(user)s, has '
                    'created an user account for you on our website, and has made you a '
                    'member of %(agora)s. If you think this user is spamming you, please '
                    'contact us.\n\nYour new username is \'%(username)s\', and your '
                    'password is \'%(password)s\'. You can now log in using these '
                    'credentials.\n\n') % dict(
                        agora=agora.get_full_name(),
                        user=self.request.user.username,
                        username=new_username,
                        password=new_password
                    ) + self.cleaned_data['welcome'],
                extra_urls=((_('Login url'),reverse('userena_signin')),)
            ))
            email = EmailMultiAlternatives(
                subject=_('%(site)s - Welcome as new member to %(agora)s') %\
                    dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[new_user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()

        return agora

    def __init__(self, request, *args, **kwargs):
        super(AgoraAddMembersForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.request = request
        self.helper.layout = Layout(Fieldset(_('Add members'), 'new_members'))
        self.helper.add_input(Submit('submit', _('Add members'), css_class='btn btn-success btn-large'))

    class Meta:
        model = Agora
        fields = ()

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

class CreateElectionForm(django_forms.ModelForm):
    question = django_forms.CharField(_("Question"), required=True)
    answers = django_forms.CharField(_("Answers"), required=True,
        help_text=_("Each choice on separate lines"), widget=django_forms.Textarea)

    from_date = django_forms.DateTimeField(label=_('Start voting'), required=False,
        help_text=_("Not required, you can choose to start the voting period manually"),
        widget=django_forms.TextInput(attrs={'class': 'datetimepicker'}),
        input_formats=('%m/%d/%Y %H:%M',))
    to_date = django_forms.DateTimeField(label=_('End voting'), required=False,
        help_text=_("Not required, you can choose to end the voting period manually"),
        widget=django_forms.TextInput(attrs={'class': 'datetimepicker'}),
        input_formats=('%m/%d/%Y %H:%M',))

    def __init__(self, request, agora, *args, **kwargs):
        super(CreateElectionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.request = request
        self.agora = agora
        self.fields['is_vote_secret'].initial = agora.is_vote_secret
        self.helper.layout = Layout(Fieldset(_('Create election'),
            'pretty_name', 'description', 'question', 'answers', 'is_vote_secret', 'from_date', 'to_date'))
        self.helper.add_input(Submit('submit', _('Create Election'),
            css_class='btn btn-success btn-large'))

    def clean(self, *args, **kwargs):
        cleaned_data = super(CreateElectionForm, self).clean()

        from_date = cleaned_data.get("from_date", None)
        to_date = cleaned_data.get("to_date", None)

        if not from_date and not to_date:
            return cleaned_data

        if (not from_date and to_date) or (from_date and not to_date):
            raise django_forms.ValidationError(_('You need to either provide '
                'none or both start and end voting dates'))

        if from_date < datetime.datetime.now():
            raise django_forms.ValidationError(_('Invalid start date, must be '
                'in the future'))

        if to_date - from_date < datetime.timedelta(hours=1):
            raise django_forms.ValidationError(_('Voting time must be at least 1 hour'))

        return cleaned_data

    def clean_answers(self, *args, **kwargs):
        data = self.cleaned_data["answers"]

        answers = [answer_value.strip()
            for answer_value in self.cleaned_data["answers"].splitlines()
                if answer_value.strip()]

        if len(answers) < 2:
            raise django_forms.ValidationError(_('You need to provide at least two '
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
        else:
            election.is_approved = False

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


        if from_date and to_date:
            kwargs=dict(
                election_id=election.id,
                is_secure=self.request.is_secure(),
                site_id=Site.objects.get_current().id,
                remote_addr=self.request.META.get('REMOTE_ADDR')
            )
            start_election.apply_async(kwargs=kwargs, task_id=election.task_id(start_election),
                eta=election.voting_starts_at_date)
            kwargs["user_id"] = self.request.user.id
            end_election.apply_async(kwargs=kwargs, task_id=election.task_id(end_election),
                eta=election.voting_ends_at_date)

        return election

    class Meta:
        model = Election
        fields = ('pretty_name', 'description', 'is_vote_secret')


class ElectionEditForm(django_forms.ModelForm):
    question = django_forms.CharField(_("Question"), required=True)
    answers = django_forms.CharField(_("Answers"), required=True,
        help_text=_("Each choice on separate lines"), widget=django_forms.Textarea)

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
        self.fields['question'].initial = instance.questions[0]['question']
        self.fields['answers'].initial = "\n".join(answer['value']
            for answer in instance.questions[0]['answers'])
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

        if from_date < datetime.datetime.now():
            raise django_forms.ValidationError(_('Invalid start date, must be '
                'in the future'))

        if to_date - from_date < datetime.timedelta(hours=1):
            raise django_forms.ValidationError(_('Voting time must be at least 1 hour'))

        return cleaned_data

    def save(self, *args, **kwargs):
        election = super(ElectionEditForm, self).save(*args, **kwargs)

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
        election.last_modified_at_date = datetime.datetime.now()
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
                remote_addr=self.request.META.get('REMOTE_ADDR')
            )
            start_election.apply_async(kwargs=kwargs, task_id=election.task_id(start_election),
                eta=election.voting_starts_at_date)
            kwargs["user_id"] = self.request.user.id
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
            raise forms.ValidationError("Sorry, you cannot vote in this election.")

        return cleaned_data

    def save(self, *args, **kwargs):
        # invalidate older votes from the same voter to the same election
        old_votes = self.election.cast_votes.filter(is_direct=True,
            invalidated_at_date=None, voter=self.request.user)
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

        if self.election.is_vote_secret and ('submit-secret' in self.request.POST) and\
            (self.request.user in self.election.agora.members.all() or\
                self.election.agora.has_perms('join', self.request.user)):
            vote.is_public = False
            vote.reason = None
        else:
            vote.reason = self.cleaned_data['reason']
            vote.is_public = True
        vote.data = data
        vote.casted_at_date = datetime.datetime.now()
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

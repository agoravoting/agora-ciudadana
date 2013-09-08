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

import random
import os
import hashlib

from django.contrib import messages
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import forms as auth_forms
from django.contrib.sites.models import Site
from django import forms as django_forms
from django.utils import translation
from django.core.mail import EmailMultiAlternatives, EmailMessage, send_mass_mail
from django.utils import simplejson as json
from django.utils import timezone

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden, Layout, Fieldset

from userena import forms as userena_forms
from userena import settings as userena_settings
from userena.models import UserenaSignup

from actstream.actions import follow
from actstream.signals import action

from agora_site.misc.utils import geolocate_ip, get_base_email_context

class AccountSignupForm(userena_forms.SignupForm):
    def __init__(self, *args, **kwargs):
        super(AccountSignupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields.insert(0, 'first_name', django_forms.CharField(label=_("Name"), required=True, max_length=30))

        # if using fnmt, we require user/pass registration to give a way to
        # verify their identity
        if settings.AGORA_ALLOW_FNMT_CERTIFICATE:
            self.fields.insert(0, 'scanned_id', django_forms.FileField(label=_("DNI escaneado"), required=True, help_text=u"Adjunta tu DNI escaneado para poder verificar tu identidad (formato pdf o imagen, max. 1MB)"))
            self.helper.form_enctype = 'multipart/form-data'

        self.helper.form_id = 'register-form'
        self.helper.form_action = 'userena_signup'

        self.helper.add_input(Submit('submit', _('Sign up'), css_class='btn btn-success btn-large'))
        self.helper.add_input(Hidden('type', 'register'))

    def handle_uploaded_file(self, f):
        file_name = "%s_%s%s" % (self.cleaned_data['username'],
            hashlib.md5(self.cleaned_data['username'] + settings.AGORA_API_AUTO_ACTIVATION_SECRET).hexdigest(),
            os.path.splitext(f.name)[1])
        file_path = os.path.join(settings.MEDIA_ROOT, 'dnis', file_name)
        with open(file_path, 'wb+') as destination:
            for chunk in f.chunks():
                destination.write(chunk)

    def save(self):
        if settings.AGORA_ALLOW_FNMT_CERTIFICATE:
            self.handle_uploaded_file(self.request.FILES['scanned_id'])
        new_user = super(AccountSignupForm, self).saveWithFirstName(auto_join_secret=True)
        signup_object = new_user.save()
        return new_user

class AcccountAuthForm(userena_forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AcccountAuthForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'login-form'
        self.helper.form_action = 'userena_signin'
        self.helper.help_text_inline = True
        self.fields['password'].help_text=_("<a href=\"%(url)s\">Forgot your "
            + "password?</a>") % dict(url=reverse('userena_password_reset'))

        self.helper.add_input(Submit('submit', _('Log in'), css_class='btn btn-success btn-large'))
        self.helper.add_input(Hidden('type', 'login'))

class AccountChangeEmailForm(userena_forms.ChangeEmailForm):
    def __init__(self, user, *args, **kwargs):
        super(AccountChangeEmailForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', _('Change email'), css_class='btn btn-success btn-large'))

        super(AccountChangeEmailForm, self).__init__(*args, **kwargs)

class AccountPasswordResetForm(auth_forms.PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super(AccountPasswordResetForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(Fieldset(_('Reset Password'), 'email'))
        self.helper.add_input(Submit('submit', _('Reset password'), css_class='btn btn-success btn-large'))

class AccountSetPasswordForm(auth_forms.SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(AccountSetPasswordForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(Fieldset(_('Set new Password'), 'new_password1', 'new_password2'))
        self.helper.add_input(Submit('submit', _('Set new password'), css_class='btn btn-success btn-large'))

class RegisterCompleteInviteForm(django_forms.Form):
    """
    Form for creating a new user account.

    Validates that the requested username and e-mail is not already in use.
    Also requires the password to be entered twice and the Terms of Service to
    be accepted.

    """
    username = django_forms.RegexField(regex=userena_forms.USERNAME_RE,
                                max_length=30,
                                widget=django_forms.TextInput(attrs=userena_forms.attrs_dict),
                                label=_("Username"),
                                error_messages={'invalid': _('Username must contain only letters, numbers, dots and underscores.')})
    password1 = django_forms.CharField(widget=django_forms.PasswordInput(attrs=userena_forms.attrs_dict,
                                                           render_value=False),
                                label=_("Create password"))
    password2 = django_forms.CharField(widget=django_forms.PasswordInput(attrs=userena_forms.attrs_dict,
                                                           render_value=False),
                                label=_("Repeat password"))

    def __init__(self, *args, **kwargs):
        self.userena_signup_obj = kwargs['userena_signup_obj']
        self.request = kwargs['request']
        del kwargs['userena_signup_obj']
        del kwargs['request']
        super(RegisterCompleteInviteForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields.insert(0, 'first_name', django_forms.CharField(label=_("Name"), required=True, max_length=30))
        self.helper.add_input(Submit('submit', _('Sign up'), css_class='btn btn-success btn-large'))

    def clean_username(self):
        """
        Validate that the username is alphanumeric and is not already in use.
        Also validates that the username is not listed in
        ``USERENA_FORBIDDEN_USERNAMES`` list.

        """
        try:
            user = User.objects.get(username__iexact=self.cleaned_data['username'])
        except User.DoesNotExist:
            pass
        else:
            raise django_forms.ValidationError(_('This username is already taken.'))
        if self.cleaned_data['username'].lower() in userena_settings.USERENA_FORBIDDEN_USERNAMES:
            raise django_forms.ValidationError(_('This username is not allowed.'))
        return self.cleaned_data['username']

    def clean(self):
        """
        Validates that the values entered into the two password fields match.
        Note that an error here will end up in ``non_field_errors()`` because
        it doesn't apply to a single field.

        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise django_forms.ValidationError(_('The two password fields didn\'t match.'))
        return self.cleaned_data

    def save(self):
        """ Creates a new user and account. Returns the newly created user. """
        username, password, first_name = (self.cleaned_data['username'],
                                     self.cleaned_data['password1'],
                                     self.cleaned_data['first_name'])

        user = self.userena_signup_obj.user
        self.userena_signup_obj.activation_key = userena_settings.USERENA_ACTIVATED
        user.is_active = True
        user.username = username
        user.set_password(password)
        user.first_name = first_name
        profile = user.get_profile()

        agora_id = profile.extra['join_agora_id']
        profile.extra = {}
        user.save()
        profile.save()
        self.userena_signup_obj.save()
        profile.add_to_agora(agora_id=agora_id, request=self.request)

        # add user to the default agoras if any
        for agora_name in settings.AGORA_REGISTER_AUTO_JOIN:
            profile.add_to_agora(agora_name=agora_name, request=self.request)

        # Sign the user in.
        auth_user = authenticate(identification=user.email,
                                check_password=False)
        login(self.request, auth_user)

        if userena_settings.USERENA_USE_MESSAGES:
            messages.success(self.request, _('Your account has been activated and you have been signed in.'), fail_silently=True)
        return user


class RegisterCompleteFNMTForm(django_forms.Form):
    """
    Form for creating a new user account.

    Validates that the requested e-mail is not already in use.
    Also requires the Terms of Service to be accepted.

    """
    email = django_forms.EmailField(max_length=40,
                                label=_("Email"))

    def __init__(self, *args, **kwargs):
        self.userena_signup_obj = kwargs['userena_signup_obj']
        self.request = kwargs['request']
        del kwargs['userena_signup_obj']
        del kwargs['request']
        super(RegisterCompleteFNMTForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', _('Sign up'), css_class='btn btn-success btn-large'))

    def clean_email(self):
        """
        Validate that the email is not already in use.

        """
        try:
            user = User.objects.get(email__iexact=self.cleaned_data['email'])
        except User.DoesNotExist:
            pass
        else:
            raise django_forms.ValidationError(_('This email is already taken.'))
        return self.cleaned_data['email']

    def save(self):
        """ Creates a new user and account. Returns the newly created user. """
        email = self.cleaned_data['email']

        user = self.userena_signup_obj.user
        self.userena_signup_obj.activation_key = userena_settings.USERENA_ACTIVATED
        # generate a valid new username
        base_username = username = slugify(email.split('@')[0])
        while User.objects.filter(username=username).exists():
            username = base_username + str(random.randint(0, 100))


        user.is_active = True
        user.username = username
        user.email = email
        profile = user.get_profile()

        user.save()
        profile.save()
        self.userena_signup_obj.save()

        # add user to the default agoras if any
        for agora_name in settings.AGORA_REGISTER_AUTO_JOIN:
            profile.add_to_agora(agora_name=agora_name, request=self.request)

        # Sign the user in.
        auth_user = authenticate(identification=user.email,
                                check_password=False)
        login(self.request, auth_user)

        if userena_settings.USERENA_USE_MESSAGES:
            messages.success(self.request, _('Your account has been activated and you have been signed in.'), fail_silently=True)
        return user


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

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden, Layout, Fieldset

from userena import forms as userena_forms
from django.contrib.auth import forms as auth_forms
from django import forms as django_forms

class AccountSignupForm(userena_forms.SignupFormOnlyEmail):
    def __init__(self, *args, **kwargs):
        super(AccountSignupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields.insert(0, 'first_name', django_forms.CharField(label=_("Name"), required=True, max_length=30))
        self.helper.form_id = 'register-form'
        self.helper.form_action = 'userena_signup'

        self.helper.add_input(Submit('submit', _('Sign up'), css_class='btn btn-success btn-large'))
        self.helper.add_input(Hidden('type', 'register'))

    def save(self):
        new_user = super(AccountSignupForm, self).save()
        new_user.first_name = self.cleaned_data['first_name']
        new_user.save()
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

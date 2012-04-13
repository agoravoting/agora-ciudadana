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

from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse_lazy
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required

from userena import views as userena_views
from userena import settings as userena_settings
from django.utils.translation import ugettext_lazy  as _

from agora_site.accounts.forms import (AccountSignupForm, AcccountAuthForm,
    AccountPasswordResetForm, AccountSetPasswordForm)
from agora_site.accounts import views as accounts_views

urlpatterns = patterns('',
    # Signup, signin and signout
    url(r'^signup/$',
        userena_views.signup,
        {
            'signup_form': AccountSignupForm,
            'template_name': 'accounts/auth_forms.html',
            'extra_context': {'login_form': AcccountAuthForm, 'action': 'register'}
        },
        name='userena_signup'
    ),
    url(r'^signin/$',
        userena_views.signin,
        {
           'auth_form': AcccountAuthForm,
           'template_name': 'accounts/signin_form.html',
           'extra_context': {'register_form': AccountSignupForm, 'action': 'login'}
        },
        name='userena_signin'
    ),
    url(r'^signout/$',
       auth_views.logout,
       {'next_page': userena_settings.USERENA_REDIRECT_ON_SIGNOUT},
       name='userena_signout'),

    # Reset password
    url(r'^password/reset/$',
       auth_views.password_reset,
       {'template_name': 'accounts/auth_basic_form.html',
        'email_template_name': 'accounts/emails/password_reset_message.txt',
        'password_reset_form': AccountPasswordResetForm,
        'post_reset_redirect': reverse_lazy('userena_password_reset_done'),
        'extra_context': {'title': _('Reset password')},
        }, 
       name='userena_password_reset'),
    url(r'^password/reset/done/$',
       accounts_views.PasswordResetDoneView.as_view(),
       name='userena_password_reset_done'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
       auth_views.password_reset_confirm,
       {'template_name': 'accounts/password_reset_confirm_form.html',
        'set_password_form': AccountSetPasswordForm,
        'post_reset_redirect': reverse_lazy('userena_password_reset_complete'),
        'extra_context': {'title': _('Reset password')},
       },
       name='userena_password_reset_confirm'),
    url(r'^password/reset/confirm/complete/$',
       accounts_views.PasswordResetCompleteView.as_view(),
       name='userena_password_reset_complete'),

    ## Signup
    url(r'^(?P<username>[\.\w]+)/signup/complete/$',
       accounts_views.SignUpCompleteView.as_view(),
       name='userena_signup_complete'),

    # Activate
    url(r'^(?P<username>[\.\w]+)/activate/(?P<activation_key>\w+)/$',
       userena_views.activate,
       {'success_url': '/',
        'template_name': 'accounts/activate_fail.html'},
       name='userena_activate'),

    # Change email and confirm it
    url(r'^(?P<username>[\.\w]+)/email/$',
       userena_views.email_change,
       name='userena_email_change'),
    url(r'^(?P<username>[\.\w]+)/email/complete/$',
       userena_views.direct_to_user_template,
       {'template_name': 'accounts/email_change_complete.html'},
       name='userena_email_change_complete'),
    url(r'^(?P<username>[\.\w]+)/confirm-email/complete/$',
       userena_views.direct_to_user_template,
       {'template_name': 'accounts/email_confirm_complete.html'},
       name='userena_email_confirm_complete'),
    url(r'^(?P<username>[\.\w]+)/confirm-email/(?P<confirmation_key>\w+)/$',
       userena_views.email_confirm,
       name='userena_email_confirm'),

    # Disabled account
    url(r'^(?P<username>[\.\w]+)/disabled/$',
       userena_views.direct_to_user_template,
       {'template_name': 'accounts/disabled.html'},
       name='userena_disabled'),

    # Change password
    url(r'^(?P<username>[\.\w]+)/password/$',
       userena_views.password_change,
       {'template_name': 'accounts/password_form.html'},
       name='userena_password_change'),
    url(r'^(?P<username>[\.\w]+)/password/complete/$',
       userena_views.direct_to_user_template,
       {'template_name': 'accounts/password_complete.html'},
       name='userena_password_change_complete'),

    # Edit profile
    #url(r'^(?P<username>[\.\w]+)/edit/$',
       #userena_views.profile_edit,
       #name='userena_profile_edit'),

    # View profiles
    #url(r'^(?P<username>(?!signout|signup|signin)[\.\w]+)/$',
       #userena_views.profile_detail,
       #name='userena_profile_detail'),
    #url(r'^page/(?P<page>[0-9]+)/$',
       #userena_views.profile_list,
       #name='userena_profile_list_paginated'),
    #url(r'^$',
       #userena_views.profile_list,
       #name='userena_profile_list'),
)

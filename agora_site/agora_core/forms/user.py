import requests

from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django import forms as django_forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils import translation, timezone
from django.contrib.markup.templatetags.markup import textile
from django.utils.translation import gettext as _
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare

from userena import settings as userena_settings
from userena import forms as userena_forms
from userena.models import UserenaSignup

from uuid import uuid4

from agora_site.misc.utils import FormRequestMixin
from agora_site.agora_core.forms.comment import COMMENT_MAX_LENGTH
from agora_site.misc.utils import (send_mass_html_mail, get_base_email_context,
                                   clean_html)

class UsernameAvailableForm(django_forms.Form, FormRequestMixin):
    def __init__(self, *args, **kwargs):
        super(UsernameAvailableForm, self).__init__(*args, **kwargs)

    def is_valid(self):
        return User.objects.filter(username=self.data["username"]).count() == 0

    class Meta:
        model = User
        fields = ('username')

class LoginForm(userena_forms.AuthenticationForm):
    def __init__(self, request, data):
        self.request = request
        return super(LoginForm, self).__init__(data=data)

    def is_valid(self):
        if super(LoginForm, self).is_valid():
            identification, password, remember_me = (self.cleaned_data['identification'],
                self.cleaned_data['password'], self.cleaned_data['remember_me'])
            user = authenticate(identification=identification, password=password)
            if user.is_active:
                login(self.request, user)
                if remember_me:
                    self.request.session.set_expiry(userena_settings.USERENA_REMEMBER_ME_DAYS[1] * 86400)
                else:
                    self.request.session.set_expiry(0)
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        return dict(request=request, data=data)

class DisableUserForm(django_forms.Form):
    '''
    Secure form to disable user, request current password if any
    '''
    password = django_forms.CharField(max_length=75, required=True)

    def __init__(self, request, data):
        self.request = request
        super(DisableUserForm, self).__init__(data=data)

    def is_valid(self):
        if  not self.request.user.is_authenticated():
            raise django_forms.ValidationError(_('Unathenticated request.'))

        if self.request.user.password != '!' and\
                not self.request.user.check_password(self.data['password']):
            raise django_forms.ValidationError(_('Invalid password.'))

        return True

    def save(self):
        self.request.user.email = str(uuid4()) + "@disabled.example.com"
        self.request.user.first_name = ""
        self.request.user.password = '!'
        self.request.user.username = str(uuid4())[:6]
        self.request.user.is_active = False
        self.request.user.save()
        auth_logout(self.request)

        return dict()

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        return dict(request=request, data=data)


class APIEmailLoginForm(django_forms.Form):
    '''
    Secure form to login using just the email of the user.
    '''
    email = django_forms.EmailField(max_length=75, required=True)
    activation_secret = django_forms.CharField(max_length=100, required=True)

    def __init__(self, request, data):
        self.request = request
        super(APIEmailLoginForm, self).__init__(data=data)

    def is_valid(self):
        if not super(APIEmailLoginForm, self).is_valid():
            return False

        if not settings.AGORA_ALLOW_API_AUTO_ACTIVATION:
            raise django_forms.ValidationError(_('Auto activation not allowed.'))

        if not constant_time_compare(self.cleaned_data['activation_secret'], settings.AGORA_API_AUTO_ACTIVATION_SECRET):
            raise django_forms.ValidationError(_('Invalid activation secret.'))

        self.user = get_object_or_404(User, email__iexact=self.cleaned_data['email'])

        return True

    def save(self):
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save()

        token = default_token_generator.make_token(self.user)
        return dict(
            url=self.request.build_absolute_uri(reverse('auto-login-token',
                kwargs=dict(username=self.user.username, token=token))))

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        return dict(request=request, data=data)


class ChangeNameForm(django_forms.Form):
    '''
    Change first name of another user, only for superusers
    '''
    first_name = django_forms.CharField(max_length=140, required=True)

    def __init__(self, request, target_user, *args, **kwargs):
        super(ChangeNameForm, self).__init__(*args, **kwargs)
        self.request = request
        self.target_user = target_user

    def is_valid(self):
        if not super(ChangeNameForm, self).is_valid():
            return False

        if not self.request.user.is_superuser:
            raise django_forms.ValidationError(_('You have no permission.'))

        return True

    def clean_first_name(self):
        '''
        Validates first_name field (which is actually user's full name). If its
        a FNMT authenticated user, this user cannot change the first name.
        '''
        if 'first_name' not in self.data:
            return None

        first_name = clean_html(self.cleaned_data['first_name'])
        if '<' in first_name or '\"' in first_name or '(' in first_name:
            raise django_forms.ValidationError(_(u'Invalid first name.'))

        profile = self.target_user.get_profile()
        if isinstance(profile.extra, dict) and\
                profile.extra.has_key('fnmt_cert') and\
                self.target_user.first_name != first_name:
            raise django_forms.ValidationError(_('FNMT users cannot change their names.'))

        return first_name

    def save(self):
        self.target_user.first_name = self.cleaned_data['first_name']
        self.target_user.save()
        return dict()

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        ret_kwargs = dict(
            request=request,
            data=data
        )
        ret_kwargs['target_user'] = get_object_or_404(User, pk=kwargs["userid"])
        return ret_kwargs


class SendMailForm(django_forms.Form):
    '''
    Base comment. This is inherited by others
    '''
    comment = django_forms.CharField(label='', max_length=COMMENT_MAX_LENGTH)

    def __init__(self, request, target_user, *args, **kwargs):
        super(SendMailForm, self).__init__(*args, **kwargs)
        self.request = request
        self.target_user = target_user

    def save(self):
        translation.activate(self.target_user.get_profile().lang_code)
        context = get_base_email_context(self.request)
        context['to'] = self.target_user
        context['from'] = self.request.user
        context['comment'] = clean_html(self.cleaned_data['comment'])
        datatuples= [(
            _('Message from %s') % self.request.user.get_profile().get_fullname(),
            render_to_string('agora_core/emails/user_mail.txt',
                context),
            render_to_string('agora_core/emails/user_mail.html',
                context),
            None,
            [self.target_user.email])
        ]

        translation.deactivate()

        send_mass_html_mail(datatuples)

        return None

    def clean_comment(self):
        """
        If COMMENTS_ALLOW_PROFANITIES is False, check that the comment doesn't
        contain anything in PROFANITIES_LIST.
        """

        if not self.request.user.is_authenticated():
            raise django_forms.ValidationError(ungettext("You must be authenticated to post a comment"))

        comment = self.cleaned_data["comment"]
        if settings.COMMENTS_ALLOW_PROFANITIES == False:
            bad_words = [w for w in settings.PROFANITIES_LIST if w in comment.lower()]
            if bad_words:
                plural = len(bad_words) > 1
                raise django_forms.ValidationError(ungettext(
                    "Watch your mouth! The word %s is not allowed here.",
                    "Watch your mouth! The words %s are not allowed here.", plural) % \
                    get_text_list(['"%s%s%s"' % (i[0], '-'*(len(i)-2), i[-1]) for i in bad_words], 'and'))

        return comment

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        ret_kwargs = dict(
            request=request,
            data=data
        )

        ret_kwargs['target_user'] = get_object_or_404(User, pk=kwargs["userid"])
        return ret_kwargs

class CustomAvatarForm(django_forms.ModelForm):
    custom_avatar = django_forms.ImageField(_('Avatar'))

    def __init__(self, request, *args, **kwargs):
        kwargs['instance'] = request.user
        self.request = request
        return super(CustomAvatarForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        from django.core.files.images import get_image_dimensions
        user = super(CustomAvatarForm, self).save(commit=False)
        profile = user.get_profile()

        avatar = self.cleaned_data['custom_avatar']
        # prevent pixel flood
        height, width = get_image_dimensions(avatar)
        if height > 1024 or width > 1024:
            raise django_forms.ValidationError(_(u'Too large dimensions.'))
        if profile.mugshot:
            profile.delete_mugshot()
        profile.mugshot = avatar
        profile.save()
        return user

    class Meta:
        model = User
        fields = ()

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        ret_kwargs = dict(
            request=request,
            data=request.POST,
            files=request.FILES
        )

        return ret_kwargs

class UserSettingsForm(django_forms.ModelForm):
    use_gravatar = django_forms.BooleanField(required=False)

    first_name = django_forms.CharField(max_length=140, required=False)

    use_initials = django_forms.BooleanField(required=False)

    short_description = django_forms.CharField(max_length=140, required=False)

    biography = django_forms.CharField(_('Biography'),
        widget=django_forms.Textarea, required=False)

    email = django_forms.EmailField(required=False)

    username = django_forms.RegexField(regex=r'^[\.\w_]+$', max_length=30, required=False)

    email_updates = django_forms.BooleanField(required=False)

    old_password = django_forms.CharField(required=False)

    password1 = django_forms.CharField(required=False)

    password2 = django_forms.CharField(required=False)

    def __init__(self, request, *args, **kwargs):
        kwargs['instance'] = request.user
        self.request = request
        self.data = kwargs['data']
        return super(UserSettingsForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        user = super(UserSettingsForm, self).save(commit=False)
        profile = user.get_profile()

        if 'use_gravatar' in self.data:
            profile.delete_mugshot()
            profile.mugshot.name = "gravatar"
        elif 'use_initials' in self.data:
            profile.delete_mugshot()
            profile.mugshot.name = "initials"

        if 'short_description' in self.data:
            profile.short_description = self.cleaned_data['short_description']

        if 'biography' in self.data:
            profile.biography = self.cleaned_data['biography']

        if 'email' in self.data:
            user.email = self.cleaned_data['email']

        if 'first_name' in self.data:
            user.first_name = self.cleaned_data['first_name']

        if 'username' in self.data:
            user.username = self.cleaned_data['username']

        if 'email_updates' in self.data:
            profile.email_updates = self.cleaned_data['email_updates']

        if 'password1' in self.data:
            user.set_password(self.cleaned_data['password1'])
        profile.save()
        user.save()
        return user

    def clean_short_description(self):
        return clean_html(self.cleaned_data['short_description'])

    def clean_email(self):
        '''
        Validate that the email is not already registered with another user
        '''
        if 'email' not in self.data:
            return None

        if self.instance.password != '!' and 'old_password' not in self.data:
            raise django_forms.ValidationError(_(u'You need to supply the old password.'))

        if User.objects.filter(email=self.cleaned_data['email']
            ).exclude(pk=self.instance.id).exists():
            raise django_forms.ValidationError(_(u'This email is already in '
                u'use. Please supply a different email.'))
        return self.cleaned_data['email']

    def clean_username(self):
        '''
        Validate that the username is not already registered with another user
        '''
        if 'username' not in self.data:
            return None

        if self.instance.password != '!' and 'old_password' not in self.data:
            raise django_forms.ValidationError(_(u'You need to supply the old password.'))

        if User.objects.filter(username=self.cleaned_data['username']
                ).exclude(pk=self.instance.id).exists():
            raise django_forms.ValidationError(_(u'This username is already in '
                u'use. Please supply a different username.'))
        return self.cleaned_data['username']

    def clean_old_password(self):
        '''
        Clean old password if needed
        '''
        if 'old_password' not in self.data:
            return None

        if self.instance.password == '!':
            return None

        if not self.instance.check_password(self.cleaned_data['old_password']):
            raise django_forms.ValidationError(_(u'Invalid password.'))
        return self.cleaned_data['old_password']


    def clean_password1(self):
        '''
        Clean old passwords match
        '''
        if 'password1' not in self.data:
            return None

        if self.instance.password != '!' and 'old_password' not in self.data:
            raise django_forms.ValidationError(_(u'You need to supply the old password.'))

        if 'password2' not in self.data or\
            self.cleaned_data['password1'] != self.data['password2'] or\
            len(self.cleaned_data['password1']) <= 3:
                raise django_forms.ValidationError(_('The two password fields'
                    ' didn\'t match or are insecure.'))

        return self.cleaned_data['password1']

    def clean_first_name(self):
        '''
        Validates first_name field (which is actually user's full name). If its
        a FNMT authenticated user, this user cannot change the first name.
        '''
        if settings.AGORA_REQUEST_SCANNED_ID_ON_REGISTER and\
                self.cleaned_data['first_name'] != self.request.user.first_name:
            return self.request.user.first_name

        if 'first_name' not in self.data:
            return None

        first_name = clean_html(self.cleaned_data['first_name'])
        if '<' in first_name or '\"' in first_name:
            raise django_forms.ValidationError(_(u'Invalid first name.'))

        profile = self.request.user.get_profile()
        if isinstance(profile.extra, dict) and\
                profile.extra.has_key('fnmt_cert') and\
                self.request.user.first_name != first_name:
            raise django_forms.ValidationError(_('FNMT users cannot change their names.'))

        return first_name

    def clean(self):
        """
        Validates that the values entered into the two password fields match.
        """
        if self.request.user.is_anonymous():
            raise django_forms.ValidationError(_('You need to be '
                'authenticated'))

        self.cleaned_data['biography'] = clean_html(self.cleaned_data['biography'])
        return self.cleaned_data

    class Meta:
        model = User
        fields = ()

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        ret_kwargs = dict(
            request=request,
            data=data
        )

        return ret_kwargs

class APISignupForm(django_forms.Form):
    """
    Form for creating a new user account.

    Validates that the requested username and e-mail is not already in use.
    Also requires the password to be entered twice and the Terms of Service to
    be accepted.

    """
    first_name = django_forms.RegexField(regex=r'^[_\.\w ]+$', max_length=140, required=True)
    username = django_forms.RegexField(regex=userena_forms.USERNAME_RE,
                                max_length=30, required=True,
                                error_messages={'invalid': _('Username must contain only letters, numbers, dots and underscores.')})
    email = django_forms.EmailField(max_length=75, required=True)
    password1 = django_forms.CharField(required=True)
    password2 = django_forms.CharField(required=True)
    activation_secret = django_forms.CharField(required=False)

    request = None

    def clean_username(self):
        """
        Validate that the username is alphanumeric and is not already in use.
        Also validates that the username is not listed in
        ``USERENA_FORBIDDEN_USERNAMES`` list.

        """
        try:
            user = User.objects.get(username=self.cleaned_data['username'])
        except User.DoesNotExist:
            pass
        else:
            raise django_forms.ValidationError(_('This username is already taken.'))
        if self.cleaned_data['username'].lower() in userena_settings.USERENA_FORBIDDEN_USERNAMES:
            raise django_forms.ValidationError(_('This username is not allowed.'))
        return self.cleaned_data['username']

    def clean_email(self):
        """ Validate that the e-mail address is unique. """
        user = User.objects.filter(email__iexact=self.cleaned_data['email'])
        if user.exists():
            user = user[0]
            if user.is_active:
                raise django_forms.ValidationError(_('This email is already in use. Please supply a different email.'))
            else:
                # sending activation email
                user.userena_signup.send_activation_email(user.userena_signup.activation_key)
                link = settings.AGORA_BASE_URL + reverse('auto_join_activate',
                    args=(user.username, user.userena_signup.activation_key))
                raise django_forms.ValidationError('This email is already in use but not activated, we have sent to the user\'s email the activation link: ' + link)
        return self.cleaned_data['email']

    def clean_activation_secret(self):
        if len(self.cleaned_data['activation_secret']) > 0:
            if not constant_time_compare(
                    self.cleaned_data['activation_secret'],
                    settings.AGORA_API_AUTO_ACTIVATION_SECRET):
                raise django_forms.ValidationError(_('Invalid activation secret.'))
            if not settings.AGORA_ALLOW_API_AUTO_ACTIVATION:
                raise django_forms.ValidationError(_('Auto activation not allowed.'))
        return self.cleaned_data['activation_secret']

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
        username, email, password = (self.cleaned_data['username'],
                                     self.cleaned_data['email'],
                                     self.cleaned_data['password1'])

        if not self.cleaned_data['activation_secret']:
            new_user = UserenaSignup.objects.create_user(username, email,
                password,
                not userena_settings.USERENA_ACTIVATION_REQUIRED,
                userena_settings.USERENA_ACTIVATION_REQUIRED)
        else:
            new_user = UserenaSignup.objects.create_user(username, email,
                password, False, False)
            new_user.first_name = self.cleaned_data['first_name'][:30]
            new_user.is_active = True
            new_user.save()
            self.token = default_token_generator.make_token(new_user)
            profile = new_user.get_profile()
            profile.extra = dict(auto_activation=True)
            profile.save()

        new_user.first_name = self.cleaned_data['first_name'][:30]
        return new_user

    def bundle_obj(self, obj, request):
        '''
        Bundles the object for the api showing activation url if needed
        '''
        from agora_site.agora_core.resources.user import (
            AutoJoinActivationUserResource, TinyUserResource)

        if not self.cleaned_data['activation_secret']:
            ur = TinyUserResource()
            bundle = ur.build_bundle(obj=obj, request=request)
            bundle = ur.full_dehydrate(bundle)
            return bundle
        else:
            ur = AutoJoinActivationUserResource(self.token)
            ur.url_name = 'auto-login-token'
            bundle = ur.build_bundle(obj=obj, request=request)
            bundle = ur.full_dehydrate(bundle)
            return bundle

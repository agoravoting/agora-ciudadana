from uuid import uuid4

from django.contrib.auth.models import User
from django.conf.urls.defaults import url
from django.core.urlresolvers import reverse
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout as auth_logout
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.views.decorators.cache import cache_control
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, EmailMessage, send_mass_mail
from django.utils import simplejson as json
from django.utils import translation
from django.db.models import Q
from django.utils import timezone
from django.contrib.sites.models import Site

from tastypie.utils import trailing_slash
from tastypie import http
from tastypie import fields
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.validation import Validation, CleanedDataFormValidation

from userena import forms as userena_forms
from userena.models import UserenaSignup

from agora_site.misc.utils import get_base_email_context
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.misc.utils import rest, validate_email
from agora_site.misc.decorators import permission_required
from agora_site.agora_core.forms.user import (UsernameAvailableForm, LoginForm,
    SendMailForm, UserSettingsForm, CustomAvatarForm, APISignupForm,
    APIEmailLoginForm, DisableUserForm, ChangeNameForm)
from agora_site.agora_core.models import Profile
from agora_site.agora_core.models import Agora


class TinyUserResource(GenericResource):
    '''
    Tiny Resource representing users.

    Typically used to include the critical user information in other
    resources, as in ActionResource for example.
    '''

    content_type = fields.CharField(default="user")
    url = fields.CharField()
    mugshot_url = fields.CharField()
    full_name = fields.CharField()
    short_description = fields.CharField()

    # if this is set to true, full name is not shown to the plebe
    make_anonymous = settings.ANONYMIZE_USERS

    class Meta(GenericMeta):
        queryset = User.objects.select_related("profile").filter(id__gt=-1)
        fields = ["username", "first_name", "id"]

    def dehydrate_url(self, bundle):
        return bundle.obj.get_profile().get_link()

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_profile().get_mugshot_url(
            force_default=self.make_anonymous)

    def dehydrate_full_name(self, bundle):
        if not self.make_anonymous:
            return bundle.obj.get_full_name()
        else:
            return _("Anonymous")

    def dehydrate_short_description(self, bundle):
        if not self.make_anonymous:
            return bundle.obj.get_profile().get_short_description()
        else:
            return _("Anonymous")


class NotAnonTinyUserResource(TinyUserResource):
    make_anonymous = False

    content_type = fields.CharField(default="user")
    url = fields.CharField()
    mugshot_url = fields.CharField()
    full_name = fields.CharField()
    short_description = fields.CharField()


class ActivationUserResource(TinyUserResource):
    activation_url = fields.CharField()

    def dehydrate_activation_url(self, bundle):
        return reverse("auto_join_activate",
            args=(bundle.obj.username, bundle.obj.userena_signup.activation_key))


class AutoJoinActivationUserResource(TinyUserResource):
    activation_url = fields.CharField()

    def __init__(self, token):
        self.token = token
        super(AutoJoinActivationUserResource, self).__init__()

    def dehydrate_activation_url(self, bundle):
        return reverse('auto-login-token',
                       args=(bundle.obj.username, self.token))


class TinyProfileResource(GenericResource):
    '''
    Tiny Resource representing profiles.

    Typically used to include the critical user information in other
    resources, as in ActionResource for example.
    '''

    # if this is set to true, full name is not shown to the plebe
    make_anonymous = settings.ANONYMIZE_USERS

    content_type = fields.CharField(default="profile")
    username = fields.CharField()
    short_description = fields.CharField()
    first_name = fields.CharField()
    user_id = fields.IntegerField()
    url = fields.CharField()
    mugshot_url = fields.CharField()
    full_name = fields.CharField()
    num_agoras = fields.IntegerField()
    num_votes = fields.IntegerField()
    permissions_on_user = fields.ApiField()

    class Meta(GenericMeta):
        queryset = Profile.objects.filter(user__id__gt=-1)
        fields = ["id"]

    def dehydrate_permissions_on_user(self, bundle):
        return bundle.obj.get_perms(bundle.request.user)

    def dehydrate_username(self, bundle):
        return bundle.obj.user.username

    def dehydrate_short_description(self, bundle):
        if not self.make_anonymous:
            return bundle.obj.get_short_description()
        else:
            return _("Anonymous")

    def dehydrate_first_name(self, bundle):
        if not self.make_anonymous:
            return bundle.obj.user.first_name
        else:
            return _("Anonymous")

    def dehydrate_user_id(self, bundle):
        return bundle.obj.user.id

    def dehydrate_url(self, bundle):
        return bundle.obj.get_link()

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_mugshot_url(force_default=self.make_anonymous)

    def dehydrate_full_name(self, bundle):
        if not self.make_anonymous:
            return bundle.obj.user.get_full_name()
        else:
            return _("Anonymous")

    def dehydrate_num_agoras(self, bundle):
        return bundle.obj.user.agoras.count()

    def dehydrate_num_votes(self, bundle):
        return bundle.obj.count_direct_votes()

class UserResource(GenericResource):
    '''
    Resource representing users.
    '''
    url = fields.CharField()
    short_description = fields.CharField()
    mugshot_url = fields.CharField()
    full_name = fields.CharField()

    # if this is set to true, full name is not shown to the plebe
    make_anonymous = settings.ANONYMIZE_USERS

    class Meta(GenericMeta):
        queryset = User.objects.select_related("profile").filter(id__gt=-1)
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get', 'put']
        excludes = ['password', 'is_staff', 'is_superuser', 'email']

    def dehydrate_url(self, bundle):
        return bundle.obj.get_profile().get_link()

    def dehydrate_full_name(self, bundle):
        if not self.make_anonymous:
            return bundle.obj.get_full_name()
        else:
            return _("Anonymous")

    def dehydrate_short_description(self, bundle):
        if not self.make_anonymous:
            return bundle.obj.get_profile().get_short_description()
        else:
            return _("Anonymous")

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_profile().get_mugshot_url(force_default=self.make_anonymous)

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/username/(?P<username>[\w\d_.-]+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),

            url(r"^(?P<resource_name>%s)/settings%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('user_settings'), name="api_user_settings"),

            url(r"^(?P<resource_name>%s)/mugshot%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=CustomAvatarForm, raw=True,
                method="POST"), name="api_user_avatar"),

            url(r"^(?P<resource_name>%s)/register%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=APISignupForm,
                method="POST"), name="api_user_register"),

            url(r"^(?P<resource_name>%s)/(?P<userid>\d+)/change_name%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=ChangeNameForm,
                method="POST"), name="api_user_change_name"),

            url(r"^(?P<resource_name>%s)/email_login%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=APIEmailLoginForm,
                method="POST"), name="api_user_email_login"),

            url(r"^(?P<resource_name>%s)/login%s$" % (self._meta.resource_name,
                trailing_slash()), self.wrap_form(
                form_class=LoginForm, method="POST"),
                name="api_username_login"),

            url(r"^(?P<resource_name>%s)/logout%s$" % (self._meta.resource_name,
                trailing_slash()), self.wrap_view('logout'),
                name="api_user_logout"),

            url(r"^(?P<resource_name>%s)/username_available%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=UsernameAvailableForm, method="GET"),
                name="api_username_available"),

            url(r"^(?P<resource_name>%s)/password_reset%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=auth_forms.PasswordResetForm),
                name="api_password_reset"),

            url(r"^(?P<resource_name>%s)/disable%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=DisableUserForm, method="POST"),
                name="api_user_disable"),

            url(r"^(?P<resource_name>%s)/agoras%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("agoras"), name="api_user_agoras"),

            url(r"^(?P<resource_name>%s)/(?P<userid>\d+)/agoras%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("agoras"), name="api_specific_user_agoras"),

            url(r"^(?P<resource_name>%s)/(?P<userid>\d+)/participated_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("get_participated_elections"), name="api_votes_participated_elections"),

            url(r"^(?P<resource_name>%s)/open_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("open_elections"), name="api_user_open_elections"),

            url(r"^(?P<resource_name>%s)/(?P<userid>\d+)/open_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("open_elections"), name="api_specific_user_open_elections"),

            url(r"^(?P<resource_name>%s)/set_username/(?P<user_list>\w[\w/;-]*)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('user_set_by_username'), name="api_user_set_by_username"),

            url(r"^(?P<resource_name>%s)/(?P<userid>\d+)/send_mail%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('send_mail'), name="api_user_send_mail"),

            url(r"^(?P<resource_name>%s)/invite%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('user_invite'), name="api_user_invite")
        ]

    @cache_control(no_cache=True)
    def logout(self, request, **kwargs):
        '''
        Log out the currently authenticated user
        '''
        try:
            auth_logout(request)
            return self.create_response(request, dict(status="success"))
        except Exception, e:
            raise ImmediateHttpResponse(response=http.HttpBadRequest())

    @permission_required('receive_mail', (Profile, 'user__id', 'userid'))
    def send_mail(self, request, **kwargs):
        '''
        Send mail to the user
        '''
        return self.wrap_form(SendMailForm)(request, **kwargs)

    @cache_control(no_cache=True)
    def user_settings(self, request, **kwargs):
        '''
            Get the properties of the user currently authenticated
        '''

        if request.method == 'GET':
            user = User.objects.get(username=request.user)
            usr = UserSettingsResource()
            bundle = usr.build_bundle(obj=user, request=request)
            bundle = usr.full_dehydrate(bundle)

            return self.create_response(request, bundle)
        elif request.method == 'PUT':
            return self.wrap_form(form_class=UserSettingsForm, method="PUT")(request, **kwargs)

    def user_set_by_username(self, request, **kwargs):
        user_list = kwargs['user_list'].split(';')
        users = User.objects.filter(username__in=user_list)
        objects = []

        for user in users:
            bundle = self.build_bundle(obj=user, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)

        object_list = {
                        'objects': objects
                      }

        return self.create_response(request, object_list)

    def user_invite(self, request, **kwargs):
        if request.method != 'POST':
            raise ImmediateHttpResponse(response=http.HttpMethodNotAllowed())
        try:
            data = self.deserialize_post_data(request)
            emails = map(str.strip, data['emails'])
            agoraid = data['agoraid']
        except:
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        agora = get_object_or_404(Agora, pk=agoraid)
        welcome_message = data.get('welcome_message', _("Welcome to this agora"))

        if not agora.has_perms('admin', request.user):
            raise ImmediateHttpResponse(response=http.HttpMethodNotAllowed())

        for email in emails:
            q = User.objects.filter(Q(email=email)|Q(username=email))
            exists = q.exists()
            if not exists and not validate_email(email):
                # invalid email address, cannot send an email there!
                raise ImmediateHttpResponse(response=http.HttpBadRequest())

        for email in emails:
            q = User.objects.filter(Q(email=email)|Q(username=email))
            exists = q.exists()
            if exists:
                # if user exists in agora, we'll add it directly
                user = q[0]
                if user in agora.members.all():
                    continue
                # if user exists in agora, we'll add it directly
                status, resp = rest('/agora/%s/action/' % agoraid,
                                    data={'action': 'add_membership',
                                          'username': user.username,
                                          'welcome_message': welcome_message},
                                    method="POST",
                                    request=request)
                if status != 200:
                    raise ImmediateHttpResponse(response=http.HttpBadRequest())
            else:
                # send invitation
                # maximum 30 characters in username
                username = str(uuid4())[:30]
                password = str(uuid4())
                user = UserenaSignup.objects.create_user(username,
                                                email,
                                                password,
                                                False,
                                                False)
                profile = user.get_profile()
                profile.lang_code = request.user.get_profile().lang_code
                profile.extra = {'join_agora_id': agoraid}
                profile.save()

                # Mail to the user
                translation.activate(user.get_profile().lang_code)
                context = get_base_email_context(request)
                context.update(dict(
                    agora=agora,
                    other_user=request.user,
                    to=user,
                    invitation_link=reverse('register-complete-invite',
                        kwargs=dict(activation_key=user.userena_signup.activation_key)),
                    welcome_message=welcome_message
                ))

                email = EmailMultiAlternatives(
                    subject=_('%(site)s - invitation to join %(agora)s') % dict(
                                site=Site.objects.get_current().domain,
                                agora=agora.get_full_name()
                            ),
                    body=render_to_string('agora_core/emails/join_invitation.txt',
                        context),
                    to=[user.email])

                email.attach_alternative(
                    render_to_string('agora_core/emails/join_invitation.html',
                        context), "text/html")
                email.send()
                translation.deactivate()

                # add user to the default agoras if any
                for agora_name in settings.AGORA_REGISTER_AUTO_JOIN:
                    profile.add_to_agora(agora_name=agora_name, request=request)


        return self.create_response(request, {})

    def agoras(self, request, **kwargs):
        '''
        Lists the agoras in which the authenticated user or the specified user
        is a member
        '''
        from .agora import TinyAgoraResource
        class AgoraPermissionsResource(TinyAgoraResource):
            agora_permissions = fields.ApiField()

            def dehydrate_agora_permissions(self, bundle):
                return bundle.obj.get_perms(bundle.request.user)

        if kwargs.has_key('userid'):
            user = get_object_or_404(User, pk=kwargs['userid'])
        else:
            user = request.user
        if user.is_anonymous():
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        return AgoraPermissionsResource().get_custom_list(request=request, queryset=user.agoras.all())

    def open_elections(self, request, **kwargs):
        '''
        Lists the open elections in which the authenticated user can participate
        '''
        from .election import ResultsElectionResource

        search = request.GET.get('q', '')

        class UserElectionResource(ResultsElectionResource):
            '''
            ElectionResource with some handy information for the user
            '''
            has_user_voted = fields.BooleanField(default=False)
            has_user_voted_via_a_delegate =fields.BooleanField(default=False) 

            def dehydrate_has_user_voted(self, bundle):
                return bundle.obj.has_user_voted(request.user)

            def dehydrate_has_user_voted_via_a_delegate(self, bundle):
                return bundle.obj.has_user_voted_via_a_delegate(request.user)

        if kwargs.has_key('userid'):
            user = get_object_or_404(User, pk=kwargs['userid'])
        else:
            user = request.user

        if user.is_anonymous():
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        queryset = user.get_profile().get_open_elections(search)
        return UserElectionResource().get_custom_list(request=request,
            queryset=queryset)

    def get_participated_elections(self, request, userid, **kwargs):
        '''
        Lists the elections in which the user participated either direct
        or indirectly
        '''
        from .election import ResultsElectionResource
        user = get_object_or_404(User, pk=userid)
        queryset = user.get_profile().get_participated_elections()
        return ResultsElectionResource().get_custom_list(request=request,
            queryset=queryset)


class UserSettingsResource(UserResource):
    '''
    Resource representing users.
    '''
    email = fields.CharField()
    biography = fields.CharField()
    email_updates = fields.BooleanField()
    has_current_password = fields.BooleanField()

    big_mugshot = fields.CharField()
    initials_mugshot = fields.CharField()
    gravatar_mugshot = fields.CharField()

    make_anonymous = False

    def dehydrate_email(self, bundle):
        return bundle.obj.email

    def dehydrate_biography(self, bundle):
        return bundle.obj.get_profile().biography

    def dehydrate_email_updates(self, bundle):
        return bundle.obj.get_profile().email_updates

    def dehydrate_has_current_password(self, bundle):
        return bundle.obj.password != '!'

    def dehydrate_big_mugshot(self, bundle):
        return bundle.obj.get_profile().get_big_mugshot()

    def dehydrate_initials_mugshot(self, bundle):
        return bundle.obj.get_profile().get_initials_mugshot()

    def dehydrate_gravatar_mugshot(self, bundle):
        return bundle.obj.get_profile().get_gravatar_mugshot()

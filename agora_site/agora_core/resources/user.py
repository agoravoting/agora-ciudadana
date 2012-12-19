from django.contrib.auth.models import User
from django.conf.urls.defaults import url
from django.core.urlresolvers import reverse
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout as auth_logout

from tastypie.utils import trailing_slash
from tastypie import http
from tastypie import fields
from tastypie.exceptions import ImmediateHttpResponse

from userena import forms as userena_forms

from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.forms.user import *
from agora_site.agora_core.models import Profile


class TinyUserResource(GenericResource):
    '''
    Tiny Resource representing users.

    Typically used to include the critical user information in other
    resources, as in ActionResource for example.
    '''

    content_type = fields.CharField(default="user")
    url = fields.CharField()

    class Meta(GenericMeta):
        queryset = User.objects.all()
        fields = ["username", "first_name", "id"]

    def dehydrate_url(self, bundle):
        return reverse("user-view",
            kwargs=dict(username=bundle.obj.username))

class TinyProfileResource(GenericResource):
    '''
    Tiny Resource representing profiles.

    Typically used to include the critical user information in other
    resources, as in ActionResource for example.
    '''

    content_type = fields.CharField(default="profile")
    username = fields.CharField()
    first_name = fields.CharField()
    user_id = fields.IntegerField()
    url = fields.CharField()

    class Meta(GenericMeta):
        queryset = Profile.objects.all()
        fields = ["id"]

    def dehydrate_username(self, bundle):
        return bundle.obj.user.username

    def dehydrate_first_name(self, bundle):
        return bundle.obj.user.first_name

    def dehydrate_user_id(self, bundle):
        return bundle.obj.user.id

    def dehydrate_url(self, bundle):
        return reverse("user-view",
            kwargs=dict(username=bundle.obj.user.username))


class UserResource(GenericResource):
    '''
    Resource representing users.
    '''
    url = fields.CharField()

    class Meta(GenericMeta):
        queryset = User.objects.filter(id__gt=-1)
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get', 'put']
        excludes = ['password', 'is_staff', 'is_superuser', 'email']

    def dehydrate_url(self, bundle):
        return reverse("user-view",
            kwargs=dict(username=bundle.obj.username))

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/username/(?P<username>[\w\d_.-]+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),

            url(r"^(?P<resource_name>%s)/settings%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('user_settings'), name="api_user_settings"),

            url(r"^(?P<resource_name>%s)/register%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=userena_forms.SignupForm,
                method="POST"), name="api_user_register"),

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
                self.wrap_view("disable"), name="api_user_disable"),

            url(r"^(?P<resource_name>%s)/agoras%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("agoras"), name="api_user_agoras"),

            url(r"^(?P<resource_name>%s)/open_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("open_elections"), name="api_user_open_elections"),

            url(r"^(?P<resource_name>%s)/set_username/(?P<user_list>\w[\w/;-]*)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('user_set_by_username'), name="api_user_set_by_username")
        ]

    def disable(self, request, **kwargs):
        '''
        Log out the currently authenticated user
        '''
        if request.user.is_anonymous():
            raise ImmediateHttpResponse(response=http.HttpResponseNotAllowed())

        request.user.is_active = False
        auth_logout(request)
        return self.create_response(request, dict(status="success"))

    def logout(self, request, **kwargs):
        '''
        Log out the currently authenticated user
        '''
        try:
            auth_logout(request)
            return self.create_response(request, dict(status="success"))
        except Exception, e:
            raise ImmediateHttpResponse(response=http.HttpResponseBadRequest())

    def user_settings(self, request, **kwargs):
        '''
            Get the properties of the user currently authenticated
        '''

        if request.method == 'GET':
            user = User.objects.get(username=request.user)
            bundle = self.build_bundle(obj=user, request=request)
            bundle = self.full_dehydrate(bundle)

            return self.create_response(request, bundle)
        elif request.method == 'PUT':
            return self.put_detail(request)

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

    def agoras(self, request, **kwargs):
        '''
        Lists the agoras in which the authenticated user is a member
        '''
        from .agora import AgoraResource
        if request.user.is_anonymous():
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        return AgoraResource().get_custom_list(request=request, queryset=request.user.agoras.all())

    def open_elections(self, request, **kwargs):
        '''
        Lists the open elections in which the authenticated user can participate
        '''
        from .election import ElectionResource

        search = request.GET.get('q', '')

        class UserElectionResource(ElectionResource):
            '''
            ElectionResource with some handy information for the user
            '''
            has_user_voted = fields.BooleanField(default=False)
            has_user_voted_via_a_delegate =fields.BooleanField(default=False) 

            def dehydrate_has_user_voted(self, bundle):
                return bundle.obj.has_user_voted(request.user)

            def dehydrate_has_user_voted_via_a_delegate(self, bundle):
                return bundle.obj.has_user_voted_via_a_delegate(request.user)

        if request.user.is_anonymous():
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        queryset = request.user.get_profile().get_open_elections(search)
        return UserElectionResource().get_custom_list(request=request,
            queryset=queryset)

from django.contrib.auth.models import User
from django.conf.urls.defaults import url
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout as auth_logout

from tastypie.utils import trailing_slash
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse

from userena import forms as userena_forms

from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.forms.user import *


class UserResource(GenericResource):
    class Meta(GenericMeta):
        queryset = User.objects.filter(id__gt=0)
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get', 'put']
        excludes = ['password', 'is_staff', 'is_superuser', 'email']

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

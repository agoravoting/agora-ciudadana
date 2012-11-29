import json

from django.contrib.auth.models import User
from django.conf.urls.defaults import url
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import views as auth_views
from tastypie.utils import trailing_slash

from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.forms.user import *

from userena import forms as userena_forms

class UserResource(GenericResource):
    class Meta(GenericMeta):
        queryset = User.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'put']
        excludes = ['password', 'is_staff', 'is_superuser']

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/username/(?P<username>[\w\d_.-]+)/$" % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),

            url(r"^(?P<resource_name>%s)/settings%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('user_settings'), name="api_user_settings"),

            url(r"^(?P<resource_name>%s)/register%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=userena_forms.SignupForm, method="GET"), name="api_user_register"),

            url(r"^(?P<resource_name>%s)/login%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=userena_forms.AuthenticationForm, method="GET"),
                name="api_username_login"),

            url(r"^(?P<resource_name>%s)/logout%s$" % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('logout'), name="api_user_logout"),

            url(r"^(?P<resource_name>%s)/username_available%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=UsernameAvailableForm, method="GET"),
                name="api_username_available"),

            url(r"^(?P<resource_name>%s)/password_reset%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(form_class=auth_forms.PasswordResetForm, method="GET"),
                name="api_password_reset"),

            url(r"^(?P<resource_name>%s)/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view("reset_confirm"),
                name="api_reset_confirm"),

            #url(r"^(?P<resource_name>%s)/forgot_password%s$" % (self._meta.resource_name, trailing_slash()),
                                                                #self.wrap_view('forgot_password'),
                                                                #name="api_forgot_password"),
            #url(r"^(?P<resource_name>%s)/reset_password%s$" % (self._meta.resource_name, trailing_slash()),
                                                               #self.wrap_view('reset_password'),
                                                               #name="api_reset_password"),
            #url(r"^(?P<resource_name>%s)/disable%s$" % (self._meta.resource_name, trailing_slash()),
                                                         #self.wrap_view('user_disable'), name="api_user_disable"),
            url(r"^(?P<resource_name>%s)/set_username/(?P<user_list>\w[\w/;-]*)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('user_set_by_username'), name="api_user_set_by_username")
        ]

    def logout(self, request, **kwargs):
        '''
        Log out the currently authenticated user
        '''
        try:
            auth_views.logout(request)
            return self.create_response(request, dict(status="success"))
        except Exception, e:
            return self.create_response(request, dict(status="failed"))

    #def reset_confirm(self, request **kwargs):
        #'''
        #Url sent to the user to confirm reset password
        #'''
        #try:
            #auth_views.password_reset_confirm(request, **kwargs)
            #return self.create_response(request, dict(status="success"))
        #except Exception, e:
            #return self.create_response(request, dict(status="failed"))

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

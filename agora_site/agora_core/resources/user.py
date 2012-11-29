import json

from django.conf.urls.defaults import *
from django.contrib.auth.models import User
from django.conf.urls.defaults import url

from tastypie.utils import trailing_slash

from agora_site.misc.generic_resource import GenericResource, GenericMeta

from agora_site.agora_core.forms.user import *


class UserResource(GenericResource):
    class Meta(GenericMeta):
        queryset = User.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'put']
        excludes = ['password', 'is_staff', 'is_superuser']

    def override_urls(self):
        return [
<<<<<<< HEAD
            url(r"^(?P<resource_name>%s)/username/(?P<username>[\w\d_.-]+)/$" % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
            url(r"^(?P<resource_name>%s)/settings%s$" % (self._meta.resource_name, trailing_slash()),
                                                         self.wrap_view('user_settings'), name="api_user_settings"),
=======
            #url(r"^(?P<resource_name>%s)/register%s$" % (self._meta.resource_name, trailing_slash()),
                                                         #self.wrap_view('register'), name="api_user_register"),
            url(r"^(?P<resource_name>%s)/username_available%s$" \
                % (self._meta.resource_name, trailing_slash()), 
                self.wrap_form(form_class=UsernameAvailableForm, method="GET"), name="api_username_available"),
            #url(r"^(?P<resource_name>%s)/forgot_password%s$" % (self._meta.resource_name, trailing_slash()),
                                                                #self.wrap_view('forgot_password'),
                                                                #name="api_forgot_password"),
            #url(r"^(?P<resource_name>%s)/reset_password%s$" % (self._meta.resource_name, trailing_slash()),
                                                               #self.wrap_view('reset_password'),
                                                               #name="api_reset_password"),
            #url(r"^(?P<resource_name>%s)/disable%s$" % (self._meta.resource_name, trailing_slash()),
                                                         #self.wrap_view('user_disable'), name="api_user_disable"),
>>>>>>> adding username checking
        ]

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
            # TODO
            pass

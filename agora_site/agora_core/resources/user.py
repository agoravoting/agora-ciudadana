from django.contrib.auth.models import User
from tastypie.utils import trailing_slash

from agora_site.misc.generic_resource import GenericResource, GenericMeta


class UserResource(GenericResource):
    class Meta(GenericMeta):
        queryset = User.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/register%s$" % (self._meta.resource_name, trailing_slash()),
                                                         self.wrap_view('register'), name="user_register"),
            url(r"^(?P<resource_name>%s)/username_available%s$" % (self._meta.resource_name, trailing_slash()),
                                                                   self.wrap_view('username_available'), name="username_available"),
            url(r"^(?P<resource_name>%s)/forgot_password%s$" % (self._meta.resource_name, trailing_slash()),
                                                                self.wrap_view('forgot_password'), name="forgot_password"),
            url(r"^(?P<resource_name>%s)/reset_password%s$" % (self._meta.resource_name, trailing_slash()),
                                                               self.wrap_view('reset_password'), name="reset_password"),
            url(r"^(?P<resource_name>%s)/disable%s$" % (self._meta.resource_name, trailing_slash()),
                                                         self.wrap_view('user_disable'), name="user_disable"),
        ]

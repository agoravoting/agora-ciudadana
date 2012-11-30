from tastypie.resources import ALL
from tastypie.utils import trailing_slash
from tastypie.paginator import Paginator

from agora_site.misc.generic_resource import GenericResource, GenericMeta
from actstream.models import user_stream
from actstream.models import Follow, Action

from django.contrib.auth.models import User
from django.conf.urls.defaults import url
from django.core.urlresolvers import reverse


class FollowResource(GenericResource):
    class Meta(GenericMeta):
        queryset = Follow.objects.all()


class ActionResource(GenericResource):
    class Meta(GenericMeta):
        queryset = Action.objects.filter(public=True)
        filtering = {
                        'action_object': ALL,
                        'actor': ALL,
                        'target': ALL
                    }

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/username/(?P<username>[\w\d_.-]+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_user_list'), name="api_user_list"),
        ]

    def get_user_list(self, request, **kwargs):
        user = User.objects.get(username=kwargs["username"])
        self.username = user.username
        self.queryset = user_stream(user)

        del kwargs["username"]
        out = self.get_list(request, **kwargs)
        delattr(self, 'queryset')
        delattr(self, 'username')

        return out

    def get_object_list(self, request):
        if not hasattr(self, 'queryset'):
            return self.Meta.queryset
        else:
            return self.queryset

    def get_resource_list_uri(self):
        if hasattr(self, 'username'):
            kwargs = {}
            kwargs['resource_name'] = self._meta.resource_name
            kwargs['username'] = self.username
            kwargs['api_name'] = self._meta.api_name
            return self._build_reverse_url("api_user_list", kwargs=kwargs)
        else:
            return super(ActionResource, self).get_resource_list_uri()

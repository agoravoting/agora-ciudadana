from tastypie.resources import ALL
from tastypie.utils import trailing_slash
from tastypie.paginator import Paginator

from actstream.models import user_stream, object_stream
from actstream.models import Follow, Action

from django.contrib.auth.models import User
from django.conf.urls.defaults import url
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType


from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.models import Agora, Election

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
            url(r"^(?P<resource_name>%s)/user/(?P<user>[\w\d_.-]+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_user_list'), name="api_user_list"),

            url(r"^(?P<resource_name>%s)/agora/(?P<agora>[0-9]+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_agora_list'), name="api_agora_list"),

            url(r"^(?P<resource_name>%s)/election/(?P<election>[0-9]+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_election_list'), name="api_election_list"),
        ]

    def get_user_list(self, request, **kwargs):
        fobject=User.objects.get(username=kwargs["user"])
        return self.get_custom_list(request=request, kwargs=kwargs,
            filter_object=fobject,
            filter_text=fobject.username,
            queryset=user_stream(fobject)
        )

    def get_agora_list(self, request, **kwargs):
        fobject=Agora.objects.get(pk=kwargs["agora"])
        return self.get_custom_list(request=request, kwargs=kwargs,
            filter_object=fobject,
            filter_text=fobject.id,
            queryset=object_stream(fobject)
        )

    def get_election_list(self, request, **kwargs):
        fobject=Election.objects.get(pk=kwargs["election"])
        return self.get_custom_list(request=request, kwargs=kwargs,
            filter_object=fobject,
            filter_text=fobject.id,
            queryset=object_stream(fobject)
        )

    def get_custom_list(self, request, filter_object, filter_text, queryset, kwargs):
        self.filter_object = filter_object
        self.filter_text = filter_text
        self.queryset = queryset

        content_type = ContentType.objects.get_for_model(self.filter_object).name
        del kwargs[content_type]
        out = self.get_list(request, **kwargs)
        delattr(self, 'queryset')
        delattr(self, 'filter_object')
        delattr(self, 'filter_text')

        return out

    def get_object_list(self, request):
        if not hasattr(self, 'queryset'):
            return self.Meta.queryset
        else:
            return self.queryset

    def get_resource_list_uri(self):
        if hasattr(self, 'filter_object'):
            content_type = ContentType.objects.get_for_model(self.filter_object).name
            kwargs = {}
            kwargs['resource_name'] = self._meta.resource_name
            kwargs[content_type] = self.filter_text
            kwargs['api_name'] = self._meta.api_name
            return self._build_reverse_url("api_%s_list" % content_type, kwargs=kwargs)
        else:
            return super(ActionResource, self).get_resource_list_uri()

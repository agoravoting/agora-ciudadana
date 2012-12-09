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
from agora_site.misc.decorators import permission_required
from agora_site.agora_core.models import Agora, Election
from agora_site.agora_core.forms import PostCommentForm

class FollowResource(GenericResource):
    class Meta(GenericMeta):
        queryset = Follow.objects.all()


class ActionResource(GenericResource):
    '''
    Resource for actions
    '''
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
                self.wrap_view('get_user_list'), name="api_action_user_list"),

            url(r"^(?P<resource_name>%s)/agora/(?P<agora>[0-9]+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_agora_list'), name="api_action_agora_list"),

            url(r"^(?P<resource_name>%s)/election/(?P<election>[0-9]+)%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_election_list'), name="api_action_election_list"),

            url(r"^(?P<resource_name>%s)/user/(?P<user>[\w\d_.-]+)/add_comment%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_form(PostCommentForm), name="api_user_add_comment"),

            url(r"^(?P<resource_name>%s)/agora/(?P<agora>[0-9]+)/add_comment%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('agora_add_comment'), name="api_agora_add_comment"),

            url(r"^(?P<resource_name>%s)/election/(?P<election>[0-9]+)/add_comment%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('election_add_comment'), name="api_election_add_comment"),
        ]

    def get_user_list(self, request, **kwargs):
        '''
        Lists an user actions
        '''
        user=User.objects.get(username=kwargs["user"])
        del kwargs["user"]

        url_args = dict(
            resource_name=self._meta.resource_name,
            api_name=self._meta.api_name,
            user=user.username
        )
        url_name="api_action_user_list"
        list_url  = self._build_reverse_url(url_name, kwargs=url_args)

        return self.get_custom_list(request=request, kwargs=kwargs,
            list_url=list_url, queryset=user_stream(user)
        )

    def get_agora_list(self, request, **kwargs):
        '''
        Lists an agora actions
        '''
        agora=Agora.objects.get(pk=kwargs["agora"])
        del kwargs["agora"]

        url_args = dict(
            resource_name=self._meta.resource_name,
            api_name=self._meta.api_name,
            agora=agora.id
        )
        url_name="api_action_agora_list"
        list_url  = self._build_reverse_url(url_name, kwargs=url_args)

        return self.get_custom_list(request=request, kwargs=kwargs,
            list_url=list_url, queryset=object_stream(agora)
        )

    def get_election_list(self, request, **kwargs):
        '''
        Lists an election actions
        '''
        election=Election.objects.get(pk=kwargs["election"])
        del kwargs["election"]

        url_args = dict(
            resource_name=self._meta.resource_name,
            api_name=self._meta.api_name,
            election=election.id
        )
        url_name="api_action_election_list"
        list_url  = self._build_reverse_url(url_name, kwargs=url_args)

        return self.get_custom_list(request=request, kwargs=kwargs,
            list_url=list_url, queryset=object_stream(election)
        )

    @permission_required('comment', (Agora, 'id', 'agora'))
    def agora_add_comment(self, request, **kwargs):
        return self.wrap_form(PostCommentForm)(request, **kwargs)

    @permission_required('comment', (Election, 'id', 'election'))
    def election_add_comment(self, request, **kwargs):
        return self.wrap_form(PostCommentForm)(request, **kwargs)

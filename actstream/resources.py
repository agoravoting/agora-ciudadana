from tastypie.resources import ALL
from tastypie.utils import trailing_slash
from tastypie.paginator import Paginator
from tastypie.resources import ModelResource
from tastypie import fields

from actstream.models import user_stream, object_stream
from actstream.models import Follow, Action

from django.contrib.auth.models import User
from django.conf.urls.defaults import url
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment

from agora_site.misc.utils import GenericForeignKeyField
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.misc.decorators import permission_required
from agora_site.agora_core.models import Agora, Election
from agora_site.agora_core.forms import PostCommentForm
from agora_site.agora_core.resources.agora import TinyAgoraResource
from agora_site.agora_core.resources.election import TinyElectionResource
from agora_site.agora_core.resources.user import TinyUserResource


class FollowResource(GenericResource):
    class Meta(GenericMeta):
        queryset = Follow.objects.all()


class TinyCommentResource(GenericResource):
    '''
    Tiny Resource representing comments.

    Typically used to include the critical comment information in other
    resources, as in ActionResource for example.
    '''
    content_type = fields.CharField(default="comment")
    class Meta(GenericMeta):
        queryset = Comment.objects.all()
        fields = ["comment", "id"]

class ActionResource(GenericResource):
    '''
    Resource for actions
    '''

    action_object = GenericForeignKeyField({
        Comment: TinyCommentResource,
        Agora: TinyAgoraResource,
        Election: TinyElectionResource,
    }, 'action_object', null=True, full=True)

    actor = GenericForeignKeyField({
        User: TinyUserResource,
    }, 'actor', full=True)


    target = GenericForeignKeyField({
        Agora: TinyAgoraResource,
        Election: TinyElectionResource,
    }, 'target', null=True, full=True)

    class Meta(GenericMeta):
        queryset = Action.objects.filter(public=True)
        filtering = {
                        'action_object': ALL,
                        'actor': ALL,
                        'target': ALL
                    }
        excludes = [
            "action_object_object_id",
            "actor_object_id",
            "target_object_id"
        ]

    def prepend_urls(self):
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

            url(r"^(?P<resource_name>%s)/election/(?P<election>[0-9]+)/add_comment%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('election_add_comment'), name="api_election_add_comment"),
        ]

    def get_user_list(self, request, **kwargs):
        '''
        Lists an user actions
        '''
        username = kwargs.get('user', '')
        try:
            user = User.objects.get(username=username)
        except:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        return self.get_custom_list(request=request, queryset=user_stream(user))

    def get_agora_list(self, request, **kwargs):
        '''
        Lists an agora actions
        '''
        agora = None
        agoraid = kwargs.get('agora', -1)
        try:
            agora = Agora.objects.get(id=agoraid)
        except:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        return self.get_custom_list(request=request, queryset=object_stream(agora))

    def get_election_list(self, request, **kwargs):
        '''
        Lists an election actions
        '''
        election = None
        electionid = kwargs.get('election', -1)
        try:
            election = Election.objects.get(id=electionid)
        except:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        return self.get_custom_list(request=request, queryset=object_stream(election))

    @permission_required('comment', (Election, 'id', 'election'))
    def election_add_comment(self, request, **kwargs):
        return self.wrap_form(PostCommentForm)(request, **kwargs)

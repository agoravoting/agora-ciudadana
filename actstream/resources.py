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
from django.contrib.markup.templatetags.markup import textile

from agora_site.misc.utils import GenericForeignKeyField
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.misc.decorators import permission_required
from agora_site.agora_core.models import Agora, Election, CastVote
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
    comment = fields.CharField()

    class Meta(GenericMeta):
        queryset = Comment.objects.all()
        fields = ["comment", "id"]

    def dehydrate_comment(self, bundle):
        return textile(bundle.obj.comment)

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

    # used to easily distinguish different kind of actions
    type_name = fields.CharField()

    vote = fields.DictField()

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
            "target_object_id",
            "ipaddr"
        ]

    def dehydrate_type_name(self, bundle):
        '''
        Handly field used to discriminate the type of action
        '''
        if bundle.obj.verb == "voted" and bundle.obj.action_object_content_type.name == "election":
            vote = CastVote.objects.get(action_id=bundle.obj.id)
            if vote.is_public and vote.is_direct and vote.is_plaintext():
                if vote.reason:
                    return "action_object_election_verb_voted_public_reason"
                else:
                    return "action_object_election_verb_voted_public"
            else:
                return "action_object_election_verb_voted"

        elif bundle.obj.action_object and bundle.obj.action_object_content_type.name == "election":
            return "action_object_election"

        elif bundle.obj.action_object and bundle.obj.action_object_content_type.name == "agora" and bundle.obj.target and bundle.obj.target_content_type.name == "user":
            return "action_object_agora_target_user"

        elif bundle.obj.action_object and bundle.obj.action_object_content_type.name == "comment" and bundle.obj.target and bundle.obj.target_content_type.name == "agora":
            return "target_agora_action_object_comment"

        elif bundle.obj.action_object and bundle.obj.action_object_content_type.name == "comment" and bundle.obj.target and bundle.obj.target_content_type.name == "election":
            return "target_election_action_object_comment"

        elif bundle.obj.action_object and bundle.obj.action_object_content_type.name == "agora":
            return "action_object_agora"

        elif bundle.obj.target and bundle.obj.target_content_type.name == "agora":
            return "target_agora"

        elif bundle.obj.target and bundle.obj.target_content_type.name == "user":
            return "target_user"

        else:
            return "unknown"

    def dehydrate_vote(self, bundle):
        '''
        Shows the vote related to the action, if any
        '''
        if bundle.obj.verb == "voted" and bundle.obj.action_object_content_type.name == "election":
            vote = CastVote.objects.get(action_id=bundle.obj.id)

            class CastVoteResource(GenericResource):
                is_changed = fields.BooleanField()
                question = fields.DictField()
                user_info = fields.DictField()

                class Meta:
                    queryset = CastVote.objects.all()
                    list_allowed_methods = []
                    detail_allowed_methods = ['get']
                    fields = ['is_public', 'is_direct', 'id', 'resource_uri', 'reason']

                def dehydrate_is_changed(self, bundle):
                    return bundle.obj.is_changed_vote()

                def dehydrate_question(self, bundle):
                    if bundle.obj.is_direct and bundle.obj.is_public and bundle.obj.is_plaintext():
                        return bundle.obj.get_first_pretty_answer()
                    else:
                        return dict()

                def dehydrate_user_info(self, bundle):
                    return dict(
                        short_description=bundle.obj.voter.get_profile().short_description,
                        num_agoras=bundle.obj.voter.agoras.count(),
                        num_votes=bundle.obj.voter.get_profile().count_direct_votes()
                    )

            cvr = CastVoteResource()
            bundle = cvr.build_bundle(obj=vote, request=bundle.request)
            bundle = cvr.full_dehydrate(bundle)
            return bundle
        else:
            return dict()

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

from agora_site.agora_core.models import Election
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource
from agora_site.agora_core.resources.agora import AgoraResource
#from agora_site.agora_core.resources.cast_vote import CastVoteResource

from tastypie import fields


DELEGATION_URL = "http://example.com/delegation/has/no/url/"


class ElectionResource(GenericResource):
    creator = fields.ForeignKey(UserResource, 'creator')
    electorate = fields.ManyToManyField(UserResource, 'electorate')
    agora = fields.ForeignKey(AgoraResource, 'agora')
    parent_election = fields.ForeignKey('self',
                                'parent_election', null=True)
    # delegated votes = fields.ManyToManyField(CastVoteResource,
    #                                          'delegated_votes')

    class Meta:
        queryset = Election.objects\
                    .exclude(url__startswith=DELEGATION_URL)\
                    .order_by('-last_modified_at_date')
        #authentication = SessionAuthentication()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

        excludes = ['PROHIBITED_ELECTION_NAMES']

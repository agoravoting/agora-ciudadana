from agora_site.agora_core.models import Election
from agora_site.agora_core.models import CastVote
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource
from agora_site.agora_core.resources.agora import AgoraResource

from tastypie import fields


DELEGATION_URL = "http://example.com/delegation/has/no/url/"
CAST_VOTE_RESOURCE = 'agora_site.agora_core.resources.castvote.CastVoteResource'


def all_votes(bundle):
    # bundle.obj is an Election
    return bundle.obj.get_all_votes()


def votes_from_delegates(bundle):
    # bundle.obj is an Election
    return bundle.obj.get_votes_from_delegates()


def direct_votes(bundle):
    # bundle.obj is an Election
    return bundle.obj.get_direct_votes()


class ElectionResource(GenericResource):
    creator = fields.ForeignKey(UserResource, 'creator')
    electorate = fields.ManyToManyField(UserResource, 'electorate')
    agora = fields.ForeignKey(AgoraResource, 'agora')
    parent_election = fields.ForeignKey('self',
                                'parent_election', null=True)
    delegated_votes = fields.ManyToManyField(CAST_VOTE_RESOURCE,
                                             'delegated_votes',
                                             full=True)
    cast_votes = fields.ToManyField(CAST_VOTE_RESOURCE,
                                             'cast_votes')
    all_votes = fields.ToManyField(CAST_VOTE_RESOURCE,
                                    attribute=all_votes, full=True,
                                    null=True)
    votes_from_delegates = fields.ToManyField(CAST_VOTE_RESOURCE,
                                    attribute=votes_from_delegates,
                                    full=True, null=True)
    direct_votes = fields.ToManyField(CAST_VOTE_RESOURCE,
                                    attribute=direct_votes,
                                    full=True, null=True)
    percentage_of_participation = fields.IntegerField()

    class Meta:
        queryset = Election.objects\
                    .exclude(url__startswith=DELEGATION_URL)\
                    .order_by('-last_modified_at_date')
        #authentication = SessionAuthentication()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

        excludes = ['PROHIBITED_ELECTION_NAMES']

    def dehydrate_percentage_of_participation(self, bundle):
        return bundle.obj.percentage_of_participation()

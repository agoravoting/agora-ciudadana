from agora_site.agora_core.models import CastVote
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource

from tastypie import fields


DELEGATION_URL = "http://example.com/delegation/has/no/url/"


class CastVoteResource(GenericResource):
    voter = fields.ForeignKey(UserResource, 'voter', full=True)
    election = fields.ForeignKey('agora_site.agora_core.resources.election.ElectionResource',
                                 'election')

    class Meta:
        queryset = CastVote.objects.all()
        #authentication = SessionAuthentication()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']
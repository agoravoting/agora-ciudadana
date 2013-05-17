from agora_site.agora_core.models.delegateelectioncount import DelegateElectionCount
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import TinyUserResource

from tastypie import fields
from tastypie.constants import ALL, ALL_WITH_RELATIONS

class DelegateElectionCountResource(GenericResource):
    delegate = fields.ForeignKey(TinyUserResource, 'delegate', full=True)
    election = fields.ForeignKey('agora_site.agora_core.resources.election.ElectionResource',
                                 'election')
    class Meta(GenericMeta):
        queryset = DelegateElectionCount.objects.all()
        fields = ['count', 'created_at_date']
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        filtering = {
            'voter': ALL,
            'election': ALL,
            'created_at_date': ALL
        }
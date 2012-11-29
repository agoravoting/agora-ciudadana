from agora_site.agora_core.models import Agora
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource

from tastypie import fields


class AgoraResource(GenericResource):
    creator = fields.ForeignKey(UserResource, 'creator', full=True)
    members = fields.ManyToManyField(UserResource, 'members', full=True)
    admins = fields.ManyToManyField(UserResource, 'admins', full=True)

    class Meta:

        queryset = Agora.objects.all()
        #authentication = SessionAuthentication()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

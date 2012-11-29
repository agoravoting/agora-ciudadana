from agora_site.agora_core.models import Agora
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource

from tastypie import fields


ELECTION_RESOURCE = 'agora_site.agora_core.resources.election.ElectionResource'


def open_elections(bundle):
    # bundle.obj is an Agora
    return bundle.obj.get_open_elections()


def tallied_elections(bundle):
    return bundle.obj.get_tallied_elections()


def all_elections(bundle):
    return bundle.obj.all_elections()


def active_delegates(bundle):
    return bundle.obj.active_delegates()


class AgoraResource(GenericResource):
    creator = fields.ForeignKey(UserResource, 'creator', full=True)
    members = fields.ManyToManyField(UserResource, 'members', full=True)
    admins = fields.ManyToManyField(UserResource, 'admins', full=True)

    open_elections = fields.ToManyField(ELECTION_RESOURCE,
                                        attribute=open_elections,
                                        null=True)

    tallied_elections = fields.ToManyField(ELECTION_RESOURCE,
                                        attribute=tallied_elections,
                                        null=True)

    all_elections = fields.ToManyField(ELECTION_RESOURCE,
                                       attribute=all_elections,
                                       null=True)

    active_delegates = fields.ToManyField(UserResource,
                                        attribute=active_delegates,
                                        null=True)

    class Meta:

        queryset = Agora.objects.all()
        #authentication = SessionAuthentication()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

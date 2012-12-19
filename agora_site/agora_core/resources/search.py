from django.contrib.auth.models import User

from tastypie import http
from tastypie import fields
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import Resource

from haystack.query import SearchQuerySet

from agora_site.misc.utils import GenericForeignKeyField
from agora_site.misc.generic_resource import (GenericResource,
    GenericResourceMixin, GenericMeta)
from agora_site.agora_core.models.agora import Agora
from agora_site.agora_core.models.election import Election
from agora_site.agora_core.models import Profile
from agora_site.agora_core.resources.agora import TinyAgoraResource
from agora_site.agora_core.resources.election import TinyElectionResource
from agora_site.agora_core.resources.user import TinyProfileResource

class SearchResource(GenericResourceMixin, Resource):
    '''
    Resource representing users.
    '''
    obj = GenericForeignKeyField({
        Agora: TinyAgoraResource,
        Election: TinyElectionResource,
        Profile: TinyProfileResource,
    }, 'object', full=True)

    class Meta(GenericMeta):
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']


    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            kwargs['id'] = bundle_or_obj.obj.object.id
        else:
            kwargs['id'] = bundle_or_obj.object.id

        return kwargs

    def get_object_list(self, request):
        return SearchQuerySet()

    def obj_get_list(self, request=None, **kwargs):
        query = request.GET.get("q", None)
        if query:
            return SearchQuerySet().auto_query(query)

        return self.get_object_list(request)

    def obj_get(self, request=None, **kwargs):
        return SearchQuerySet().filter(id=kwargs['id'])[0]

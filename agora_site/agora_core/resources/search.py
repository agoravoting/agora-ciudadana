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
from agora_site.agora_core.models.castvote import CastVote
from agora_site.agora_core.models import Profile
from agora_site.agora_core.resources.agora import TinyAgoraResource
from agora_site.agora_core.resources.election import TinyElectionResource
from agora_site.agora_core.resources.user import TinyProfileResource

class SearchResource(GenericResourceMixin, Resource):
    '''
    Resource used for general search, internally uses Haystack.

    It allows searching using the GET param "q". I.e. /search/?q=foobar

    Loosely based on http://django-tastypie.readthedocs.org/en/latest/non_orm_data_sources.html
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
        '''
        processes kwargs for detail uris. TastyPie's Resource class requires
        an implementation of this function to work.
        '''
        kwargs = {}

        # We save object id in kwargs so that def obj_get can use it, as in
        # tastypie documentation example
        if isinstance(bundle_or_obj, Bundle):
            kwargs['id'] = bundle_or_obj.obj.object.id
        else:
            kwargs['id'] = bundle_or_obj.object.id

        return kwargs

    def get_search_query_set(self, request):
        model = request.GET.get("model", None)
        models = {'agora': Agora,
                  'castvote': CastVote,
                  'election': Election
                 }
        if model and model in models:
            return SearchQuerySet().models(models[model])

        return SearchQuerySet()

    def get_object_list(self, request):
        '''
        By default search lists all objects in haystack
        '''
        return self.get_search_query_set(request)

    def obj_get_list(self, request=None, **kwargs):
        '''
        Returns a filtered object lists. Allows filtering using a query string
        using the GET param "q"
        '''

        query = request.GET.get("q", None)

        if query:
            q = self.get_search_query_set(request)
            q = q.auto_query(query)
            return q

        return self.get_object_list(request)

    def obj_get(self, request=None, **kwargs):
        '''
        Retrieves a detailed search item
        '''
        return SearchQuerySet().filter(id=kwargs['id'])[0]

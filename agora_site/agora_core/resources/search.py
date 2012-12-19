from django.contrib.auth.models import User

from tastypie import http
from tastypie import fields
from tastypie.exceptions import ImmediateHttpResponse

from haystack.query import SearchQuerySet

from agora_site.misc.generic_resource import GenericResource, GenericMeta


class TinyUserResource(GenericResource):
    '''
    Tiny Resource representing users.

    Typically used to include the critical user information in other
    resources, as in ActionResource for example.
    '''

    content_type = fields.CharField(default="user")
    class Meta(GenericMeta):
        queryset = User.objects.all()
        fields = ["username", "first_name", "id"]

class UserResource(GenericResource):
    '''
    Resource representing users.
    '''

    class Meta(GenericMeta):
        queryset = User.objects.filter(id__gt=0)
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']

    def agoras(self, request, **kwargs):
        '''
        Lists the agoras in which the authenticated user is a member
        '''
        from .agora import AgoraResource
        if request.user.is_anonymous():
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        return AgoraResource().get_custom_list(request=request, queryset=request.user.agoras.all())

    def open_elections(self, request, **kwargs):
        '''
        Lists the open elections in which the authenticated user can participate
        '''
        from .election import ElectionResource

        search = request.GET.get('q', '')

        queryset = request.user.get_profile().get_open_elections(search)
        return UserElectionResource().get_custom_list(request=request,
            queryset=queryset)

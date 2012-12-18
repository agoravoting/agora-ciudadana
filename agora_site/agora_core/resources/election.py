from django.conf.urls.defaults import url

from tastypie import fields, http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.utils import trailing_slash

from agora_site.agora_core.models import Election
from agora_site.agora_core.models import CastVote
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource
from agora_site.agora_core.resources.agora import AgoraResource
from agora_site.agora_core.resources.castvote import CastVoteResource


DELEGATION_URL = "http://example.com/delegation/has/no/url/"
CAST_VOTE_RESOURCE = 'agora_site.agora_core.resources.castvote.CastVoteResource'

class ElectionResource(GenericResource):
    creator = fields.ForeignKey(UserResource, 'creator')

    electorate = fields.ManyToManyField(UserResource, 'electorate')

    agora = fields.ForeignKey(AgoraResource, 'agora')

    parent_election = fields.ForeignKey('self', 'parent_election', null=True)

    percentage_of_participation = fields.IntegerField()

    class Meta:
        queryset = Election.objects\
                    .exclude(url__startswith=DELEGATION_URL)\
                    .order_by('-last_modified_at_date')
        #authentication = SessionAuthentication()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

        excludes = ['PROHIBITED_ELECTION_NAMES']

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<electionid>\d+)/all_votes%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_all_votes'), name="api_election_all_votes"),

            url(r"^(?P<resource_name>%s)/(?P<electionid>\d+)/cast_votes%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_cast_votes'), name="api_election_cast_votes"),

            url(r"^(?P<resource_name>%s)/(?P<electionid>\d+)/delegated_votes%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_delegated_votes'), name="api_election_delegated_votes"),

            url(r"^(?P<resource_name>%s)/(?P<electionid>\d+)/votes_from_delegates%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_votes_from_delegates'), name="api_election_votes_from_delegates"),

            url(r"^(?P<resource_name>%s)/(?P<electionid>\d+)/direct_votes%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_direct_votes'), name="api_election_direct_votes"),
        ]

    def get_all_votes(self, request, **kwargs):
        '''
        List all the votes in this agora
        '''
        return self.get_custom_resource_list(request, resource=CastVoteResource,
            queryfunc=lambda election: election.get_all_votes(), **kwargs)

    def get_cast_votes(self, request, **kwargs):
        '''
        List votes in this agora
        '''
        return self.get_custom_resource_list(request, resource=CastVoteResource,
            queryfunc=lambda election: election.cast_votes.all(), **kwargs)

    def get_delegated_votes(self, request, **kwargs):
        '''
        List votes in this agora
        '''
        return self.get_custom_resource_list(request, resource=CastVoteResource,
            queryfunc=lambda election: election.delegated_votes.all(), **kwargs)

    def get_votes_from_delegates(self, request, **kwargs):
        '''
        List votes in this agora
        '''
        return self.get_custom_resource_list(request, resource=CastVoteResource,
            queryfunc=lambda election: election.get_votes_from_delegates(), **kwargs)

    def get_direct_votes(self, request, **kwargs):
        '''
        List votes in this agora
        '''
        return self.get_custom_resource_list(request, resource=CastVoteResource, 
            queryfunc=lambda election: election.get_direct_votes(), **kwargs)

    def get_custom_resource_list(self, request, url_name, queryfunc, resource, **kwargs):
        '''
        List custom resources (mostly used for votes)
        '''
        election = None
        electionid = kwargs.get('electionid', -1)
        try:
            election = Election.objects.get(id=election)
        except:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        return resource().get_custom_list(request=request, kwargs=kwargs,
            queryset=queryfunc(election))


    def dehydrate_percentage_of_participation(self, bundle):
        return bundle.obj.percentage_of_participation()

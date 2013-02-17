from django.conf.urls.defaults import url
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives, EmailMessage, send_mass_mail
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.utils import simplejson as json
from django.utils import translation

from tastypie import fields, http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.utils import trailing_slash

from actstream.signals import action

from agora_site.agora_core.models import Election
from agora_site.agora_core.models import CastVote
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource
from agora_site.agora_core.resources.agora import AgoraResource, TinyAgoraResource
from agora_site.agora_core.resources.castvote import CastVoteResource
from agora_site.misc.utils import geolocate_ip, get_base_email_context
from agora_site.misc.decorators import permission_required


DELEGATION_URL = "http://example.com/delegation/has/no/url/"
CAST_VOTE_RESOURCE = 'agora_site.agora_core.resources.castvote.CastVoteResource'


class TinyElectionResource(GenericResource):
    '''
    Tiny Resource representing elections.

    Typically used to include the critical election information in other
    resources, as in ActionResource for example.
    '''

    content_type = fields.CharField(default="election")
    agora = fields.ForeignKey(TinyAgoraResource, 'agora', full=True)
    url = fields.CharField()
    mugshot_url = fields.CharField()

    class Meta(GenericMeta):
        queryset = Election.objects.all()
        fields = ['name', 'pretty_name', 'id', 'short_description']

    def dehydrate_url(self, bundle):
        return bundle.obj.get_link()

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_mugshot_url()


class ElectionResource(GenericResource):
    '''
    Resource representing elections.
    '''

    creator = fields.ForeignKey(UserResource, 'creator')

    electorate = fields.ManyToManyField(UserResource, 'electorate')

    agora = fields.ForeignKey(TinyAgoraResource, 'agora', full=True)

    parent_election = fields.ForeignKey('self', 'parent_election', null=True)

    percentage_of_participation = fields.IntegerField()

    url = fields.CharField()

    mugshot_url = fields.CharField()

    class Meta:
        queryset = Election.objects\
                    .exclude(url__startswith=DELEGATION_URL)\
                    .order_by('-last_modified_at_date')
        #authentication = SessionAuthentication()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

        excludes = ['PROHIBITED_ELECTION_NAMES']

    def dehydrate_url(self, bundle):
        return bundle.obj.get_link()

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_mugshot_url()

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

            url(r"^(?P<resource_name>%s)/(?P<electionid>\d+)/action%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('action'), name="api_election_action"),
        ]


    def action(self, request, **kwargs):
        '''
        Requests an action on this election

        actions:
            DONE
            * get_permissions

            TODO
            * approve
            * freeze
            * start
            * stop
            * archive
            * vote
            * cancel_vote
        '''

        actions = {
            'get_permissions': self.get_permissions_action,
            'approve': self.approve_action,
        }

        if request.method != "POST":
            raise ImmediateHttpResponse(response=http.HttpMethodNotAllowed())

        data = self.deserialize_post_data(request)

        election = None
        electionid = kwargs.get('electionid', -1)
        try:
            election = Election.objects.get(id=electionid)
        except:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        action = data.get("action", False)

        if not action or not action in actions:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        kwargs.update(data)
        return actions[action](request, election, **kwargs)


    def get_permissions_action(self, request, election, **kwargs):
        '''
        Returns the permissions the user that requested it has
        '''
        return self.create_response(request,
            dict(permissions=election.get_perms(request.user)))


    @permission_required('approve_election', (Election, 'id', 'electionid'))
    def approve_action(self, request, election, **kwargs):
        '''
        Requests membership from authenticated user to an agora
        '''
        election.is_approved = True
        election.save()

        action.send(request.user, verb='approved', action_object=election,
            target=election.agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            translation.activate(request.user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=election.agora,
                other_user=request.user,
                notification_text=_('Election %(election)s approved at agora '
                    '%(agora)s. Congratulations!') % dict(
                        agora=election.agora.get_full_name(),
                        election=election.pretty_name
                    ),
                to=request.user,
                extra_urls=[dict(
                    url_title=_("Election URL"),
                    url=election.get_link()
                )]
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - Election %(election)s approved') % dict(
                            site=Site.objects.get_current().domain,
                            election=election.pretty_name
                        ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[request.user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        return self.create_response(request, dict(status="success"))


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

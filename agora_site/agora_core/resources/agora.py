import re
import datetime

from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.cache import cache_control
from django.forms import ModelForm
from django.conf import settings
from django.core.urlresolvers import reverse
from django.conf.urls.defaults import url
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives, EmailMessage, send_mass_mail
from django.template.loader import render_to_string
from django.shortcuts import redirect, get_object_or_404, render_to_response
from django.utils.translation import ugettext as _
from django.utils import simplejson as json
from django.utils import translation
from django.utils import timezone

from tastypie import fields
from tastypie.validation import Validation, CleanedDataFormValidation
from tastypie.utils import trailing_slash
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.constants import ALL

from actstream.actions import follow, unfollow, is_following
from actstream.models import (object_stream, election_stream, Action,
    user_stream, actor_stream)
from actstream.signals import action

from guardian.shortcuts import assign, remove_perm

from agora_site.agora_core.models import Agora, CastVote
from agora_site.agora_core.tasks.agora import (send_request_membership_mails,
    send_request_admin_membership_mails, send_mail_to_members)
from agora_site.agora_core.resources.user import TinyUserResource
from agora_site.agora_core.forms import PostCommentForm, CreateElectionForm
from agora_site.agora_core.forms.agora import DelegateVoteForm
from agora_site.agora_core.views import AgoraActionJoinView
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.misc.decorators import permission_required
from agora_site.misc.utils import (geolocate_ip, get_base_email_context,
                                   clean_html)

class TinyAgoraResource(GenericResource):
    '''
    Tiny Resource representing agoras.

    Typically used to include the critical agora information in other
    resources, as in ActionResource for example.
    '''

    content_type = fields.CharField(default="agora")
    full_name = fields.CharField()
    mugshot_url = fields.CharField()

    class Meta(GenericMeta):
        queryset = Agora.objects.select_related("creator").all()
        fields = ['name', 'pretty_name', 'id', 'short_description', 'url',
                  'full_name', 'mugshot_url', 'delegation_policy']

    def dehydrate_full_name(self, bundle):
        return bundle.obj.get_full_name()

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_mugshot_url()


class CreateAgoraForm(ModelForm):
    '''
    Form used to validate the user information in the
    agora creation.
    '''
    def clean_short_description(self):
        return clean_html(self.cleaned_data['short_description'])

    def clean_pretty_name(self):
        return clean_html(self.cleaned_data['pretty_name'])

    class Meta(GenericMeta):
        model = Agora
        fields = ('pretty_name', 'short_description', 'is_vote_secret')


class AgoraAdminForm(ModelForm):
    '''
    Form used to validate agora administration details.
    '''
    def clean_short_description(self):
        return clean_html(self.cleaned_data['short_description'])

    def clean_pretty_name(self):
        return clean_html(self.cleaned_data['pretty_name'], True)

    def clean_biography(self):
        return clean_html(self.cleaned_data['biography'])

    class Meta(GenericMeta):
        model = Agora
        fields = ('pretty_name', 'short_description', 'is_vote_secret',
            'biography', 'membership_policy', 'comments_policy',
            'delegation_policy', 'featured_election')


class AgoraValidation(Validation):
    '''
    Validation class that uses some django forms to validate PUT and POST
    methods.
    '''
    def is_valid(self, bundle, request):
        if not bundle.data:
            return {'__all__': 'Not quite what I had in mind.'}

        if request.method == "POST":
            return self.validate_post(bundle, request)
        elif request.method == "PUT":
            return self.validate_put(bundle, request)

        return {}

    def validate_put(self, bundle, request):
        form = CleanedDataFormValidation(form_class=AgoraAdminForm)
        return form.is_valid(bundle, request)

    def validate_post(self, bundle, request):
        form = CleanedDataFormValidation(form_class=CreateAgoraForm)
        return form.is_valid(bundle, request)


class AgoraResource(GenericResource):
    '''
    Resource for representing agoras.
    '''
    creator = fields.ForeignKey(TinyUserResource, 'creator', full=True)
    full_name = fields.CharField()
    mugshot_url = fields.CharField()
    open_elections_count = fields.IntegerField()
    members_count = fields.IntegerField()

    class Meta(GenericMeta):
        queryset = Agora.objects.select_related(depth=1).all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'delete']
        validation = AgoraValidation()
        filtering = { "name": ALL, }

    get_list = TinyAgoraResource().get_list

    def dehydrate_full_name(self, bundle):
        return bundle.obj.get_full_name()

    def dehydrate_open_elections_count(self, bundle):
        return bundle.obj.open_elections().count()

    def dehydrate_members_count(self, bundle):
        return bundle.obj.members.count()

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_mugshot_url()

    @permission_required('create', check_static=Agora)
    def obj_create(self, bundle, **kwargs):
        self.is_valid(bundle)
        if bundle.errors:
            raise ImmediateHttpResponse(response=self.error_response(
                bundle.request, bundle.errors))

        pretty_name = clean_html(bundle.data['pretty_name'])
        short_description = clean_html(bundle.data['short_description'])
        is_vote_secret = bundle.data['is_vote_secret']

        agora = Agora(pretty_name=pretty_name,
                      short_description=short_description,
                      is_vote_secret=is_vote_secret)
        agora.create_name(bundle.request.user)
        agora.creator = bundle.request.user
        agora.url = bundle.request.build_absolute_uri(reverse('agora-view',
            kwargs=dict(username=agora.creator.username, agoraname=agora.name)))

        # we need to save before add members
        agora.save()

        agora.members.add(bundle.request.user)
        agora.admins.add(bundle.request.user)

        bundle = self.build_bundle(obj=agora, request=bundle.request)
        bundle = self.full_dehydrate(bundle)
        return bundle

    @permission_required('delete', (Agora, 'id', 'pk'))
    def obj_delete(self, bundle, **kwargs):
        return super(AgoraResource, self).obj_delete(bundle, **kwargs)

    @permission_required('admin', (Agora, 'id', 'pk'))
    def obj_update(self, bundle, **kwargs):
        self.is_valid(bundle)
        if bundle.errors:
            raise ImmediateHttpResponse(response=self.error_response(
                bundle.request, bundle.errors))

        agora = Agora.objects.get(**kwargs)
        for k, v in bundle.data.items():
            setattr(agora, k, v)
        agora.save()

        bundle = self.build_bundle(obj=agora, request=bundle.request)
        bundle = self.full_dehydrate(bundle)
        return bundle

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/action%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('action'), name="api_agora_action"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/members%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_member_list'), name="api_agora_member_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/authorities%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_authorities_list'), name="api_agora_authorities_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/admins%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_admin_list'), name="api_agora_admin_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/membership_requests%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_request_list'), name="api_agora_request_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/denied_membership_requests%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_denied_request_list'), name="api_agora_denied_request_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/admin_membership_requests%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_admin_request_list'), name="api_agora_admin_request_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/active_delegates%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_active_delegates_list'), name="api_agora_active_delegate_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/all_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_all_elections_list'), name="api_agora_all_elections_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/tallied_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_tallied_elections_list'), name="api_agora_tallied_elections_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/open_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_open_elections_list'), name="api_agora_open_elections_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/requested_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_requested_elections_list'), name="api_agora_requested_elections_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/archived_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_archived_elections_list'), name="api_agora_archived_elections_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/approved_elections%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_approved_elections_list'), name="api_agora_approved_elections_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/comments%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_comments'), name="api_agora_comments"),

            url(r"^(?P<resource_name>%s)/(?P<agora>\d+)/add_comment%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('add_comment'), name="api_agora_add_comment"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/detail%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_detail'), name="api_agora_detail"),

        ]

    def get_comments(self, request, **kwargs):
        '''
        List the comments in this agora
        '''
        from actstream.resources import ActionResource
        return self.get_custom_resource_list(request, resource=ActionResource,
            queryfunc=lambda agora: object_stream(agora, verb='commented'), **kwargs)

    @permission_required('comment', (Agora, 'id', 'agora'))
    def add_comment(self, request, **kwargs):
        '''
        Form to add comments
        '''
        return self.wrap_form(PostCommentForm)(request, **kwargs)

    def filter_user(self, request, query):
        u_filter = request.GET.get('username', '')
        if u_filter:
            q = (Q(username__icontains=u_filter) |
                 Q(first_name__icontains=u_filter) |
                 Q(last_name__icontains=u_filter))
            return query.filter(q)
        return query

    def get_admin_list(self, request, **kwargs):
        '''
        List admin members of this agora
        '''
        return self.get_custom_resource_list(request,
            resource=TinyUserResource,
            queryfunc=lambda agora: self.filter_user(request, agora.admins.all()),
            **kwargs)

    def get_member_list(self, request, **kwargs):
        '''
        List the members of this agora
        '''
        return self.get_custom_resource_list(request,
            resource=TinyUserResource,
            queryfunc=lambda agora: self.filter_user(request, agora.members.all()),
            **kwargs)

    def get_authorities_list(self, request, **kwargs):
        '''
        List the authorities of this agora
        '''
        from authority import AuthorityResource
        return self.get_custom_resource_list(request,
            resource=AuthorityResource,
            queryfunc=lambda agora: agora.agora_local_authorities.all(),
            **kwargs)

    def get_active_delegates_list(self, request, **kwargs):
        '''
        List currently active delegates in this agora
        '''
        return self.get_custom_resource_list(request,
            resource=TinyUserResource,
            queryfunc=lambda agora: self.filter_user(request, agora.active_delegates()),
            **kwargs)

    def get_all_elections_list(self, request, **kwargs):
        '''
        List all elections in an agora
        '''
        from agora_site.agora_core.resources.election import TinyElectionResource
        return self.get_custom_resource_list(request, resource=TinyElectionResource,
            queryfunc=lambda agora: agora.all_elections(), **kwargs)

    def get_tallied_elections_list(self, request, **kwargs):
        '''
        List elections that have been already tallied in an agora
        '''
        from agora_site.agora_core.resources.election import ResultsElectionResource
        return self.get_custom_resource_list(request, resource=ResultsElectionResource,
            queryfunc=lambda agora: agora.get_tallied_elections(), **kwargs)

    def get_open_elections_list(self, request, **kwargs):
        '''
        List the elections that are currently opened in an agora
        '''
        from agora_site.agora_core.resources.election import TinyElectionResource
        return self.get_custom_resource_list(request, resource=TinyElectionResource,
            queryfunc=lambda agora: agora.get_open_elections(), **kwargs)

    def get_requested_elections_list(self, request, **kwargs):
        '''
        List the elections that are currently requested in an agora
        '''
        from agora_site.agora_core.resources.election import TinyElectionResource
        return self.get_custom_resource_list(request, resource=TinyElectionResource,
            queryfunc=lambda agora: agora.requested_elections(), **kwargs)

    def get_archived_elections_list(self, request, **kwargs):
        '''
        List the elections that have been archived in an agora
        '''
        from agora_site.agora_core.resources.election import TinyElectionResource
        return self.get_custom_resource_list(request, resource=TinyElectionResource,
            queryfunc=lambda agora: agora.archived_elections(), **kwargs)

    def get_approved_elections_list(self, request, **kwargs):
        '''
        List the elections that are currently opened in an agora
        '''
        from agora_site.agora_core.resources.election import TinyElectionResource
        return self.get_custom_resource_list(request, resource=TinyElectionResource,
            queryfunc=lambda agora: agora.approved_elections(), **kwargs)

    def get_request_list(self, request, **kwargs):
        '''
        List agora membership requests
        '''

        def get_queryset(agora):
            from guardian.shortcuts import get_users_with_perms
            u_filter = request.GET.get('username', '')
            users = get_users_with_perms(agora, attach_perms=True)
            users = [k.username for k, v in users.items() if "requested_membership" in v]                       
            queryset = self.filter_user(request, User.objects.filter(username__in=users))
            return queryset

        return self.get_custom_resource_list(request, queryfunc=get_queryset,
            resource=TinyUserResource, **kwargs)

    def get_denied_request_list(self, request, **kwargs):
        '''
        List agora denied membership requests
        '''

        def get_queryset(agora):
            from guardian.shortcuts import get_users_with_perms
            users = get_users_with_perms(agora, attach_perms=True)
            users = [k.username for k, v in users.items() if "denied_requested_membership" in v]
            queryset = self.filter_user(request, User.objects.filter(username__in=users))
            return queryset

        return self.get_custom_resource_list(request, queryfunc=get_queryset,
            resource=TinyUserResource, **kwargs)

    @permission_required('admin', (Agora, 'id', 'agoraid'))
    @cache_control(no_cache=True)
    def get_admin_request_list(self, request, **kwargs):
        '''
        List agora admin membership requests
        '''

        def get_queryset(agora):
            from guardian.shortcuts import get_users_with_perms
            users = get_users_with_perms(agora, attach_perms=True)
            users = [k.username for k, v in users.items() if "requested_admin_membership" in v]
            queryset = self.filter_user(request, User.objects.filter(username__in=users))
            return queryset

        return self.get_custom_resource_list(request, queryfunc=get_queryset,
            resource=TinyUserResource, **kwargs)

    def get_custom_resource_list(self, request, queryfunc, resource=None,
        resourcefunc=None, **kwargs):
        '''
        List users
        '''
        agora = None
        agoraid = kwargs.get('agoraid', -1)
        try:
            agora = Agora.objects.get(id=agoraid)
        except:
            raise ImmediateHttpResponse(response=http.HttpNotFound())


        if resourcefunc:
            resource_instance = resourcefunc(agora, request.user)
        else:
            resource_instance = resource()

        return resource_instance.get_custom_list(request=request,
            queryset=queryfunc(agora))

    def action(self, request, **kwargs):
        '''
        Requests an action on this agora

        actions:
            DONE
            * get_permissions

            * request_membership
            * join
            * leave
            * cancel_membership_request
            * accept_membership
            * deny_membership
            * add_membership
            * remove_membership

            * request_admin_membership
            * cancel_admin_membership_request
            * accept_admin_membership
            * deny_admin_membership
            * add_admin_membership
            * remove_admin_membership
            * leave_admin_membership

            * create_election

            * delegate_vote
            * cancel_vote_delegation

            * set_authorities

            TODO
            * approve_election
            * deny_election
        '''

        actions = {
            'get_permissions': self.get_permissions_action,
            'test': self.test_action,
            'mail_to_members': self.mail_to_members,

            'request_membership': self.request_membership_action,
            'cancel_membership_request': self.cancel_membership_request_action,
            'join': self.join_action,
            'leave': self.leave_action,
            'accept_membership': self.accept_membership_action,
            'deny_membership': self.deny_membership_action,
            'add_membership': self.add_membership_action,
            'remove_membership': self.remove_membership_action,

            'request_admin_membership': self.request_admin_membership_action,
            'cancel_admin_membership_request': self.cancel_admin_membership_request_action,
            'accept_admin_membership': self.accept_admin_membership_action,
            'deny_admin_membership': self.deny_admin_membership_action,
            'add_admin_membership': self.add_admin_membership_action,
            'remove_admin_membership': self.remove_admin_membership_action,
            'leave_admin_membership': self.leave_admin_action,

            'create_election': self.create_election_action,
            'set_authorities': self.set_authorities_action,

            'delegate_vote': self.delegate_vote_action,
            'cancel_vote_delegation': self.cancel_vote_delegation,
        }

        if request.method != "POST":
            raise ImmediateHttpResponse(response=http.HttpMethodNotAllowed())

        data = self.deserialize_post_data(request)

        agora = None
        agoraid = kwargs.get('agoraid', -1)
        try:
            agora = Agora.objects.get(id=agoraid)
        except:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        action = data.get("action", False)

        if not action or not action in actions:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        kwargs.update(data)
        return actions[action](request, agora, **kwargs)

    def get_permissions_action(self, request, agora, **kwargs):
        '''
        Returns the permissions the user that requested it has
        '''
        user = request.user
        if 'userid' in kwargs:
            if not agora.has_perms('admin', request.user):
                return self.create_response(request,
                    dict(permissions=[]))
            user = get_object_or_404(User, id=kwargs['userid'])

        return self.create_response(request,
            dict(permissions=agora.get_perms(user)))

    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def mail_to_members(self, request, agora, receivers, subject, body, **kwargs):
        '''
        Mail to members
        '''
        if receivers not in ['members', 'admins', 'delegates',
            'non-delegates', 'requested-membership', 'unconfirmed-open-votes']:
            raise ImmediateHttpResponse(response=http.HttpBadRequest())

        if not isinstance(subject, basestring) or len(subject) == 0 or\
                not isinstance(body, basestring) or len(body) == 0:
            raise ImmediateHttpResponse(response=http.HttpBadRequest())

        kwargs=dict(
            agora_id=agora.id,
            user_id=request.user.id,
            is_secure=request.is_secure(),
            receivers=receivers,
            subject=subject,
            body=clean_html(body),
            site_id=Site.objects.get_current().id,
            remote_addr=request.META.get('REMOTE_ADDR')
        )
        send_mail_to_members.apply_async(kwargs=kwargs)
        return self.create_response(request, dict(status="success"))

    @permission_required('request_membership', (Agora, 'id', 'agoraid'))
    def request_membership_action(self, request, agora, **kwargs):
        '''
        Requests membership from authenticated user to an agora
        '''
        assign('requested_membership', request.user, agora)

        action.send(request.user, verb='requested membership', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        if not is_following(request.user, agora):
            follow(request.user, agora, actor_only=False, request=request)

        kwargs=dict(
            agora_id=agora.id,
            user_id=request.user.id,
            is_secure=request.is_secure(),
            site_id=Site.objects.get_current().id,
            remote_addr=request.META.get('REMOTE_ADDR')
        )
        send_request_membership_mails.apply_async(kwargs=kwargs)

        return self.create_response(request, dict(status="success"))

    @permission_required('cancel_membership_request', (Agora, 'id', 'agoraid'))
    def cancel_membership_request_action(self, request, agora, **kwargs):
        '''
        Cancel a membership request from the given username user in an agora
        '''
        # remove the request membership status and add user to the agora
        remove_perm('requested_membership', request.user, agora)

        # create an action for the event
        action.send(request.user, verb='canceled requested membership',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=request.user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            translation.activate(request.user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('You canceled your membership request at '
                    '%(agora)s') % dict(
                        agora=agora.get_full_name()
                    ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - canceled your membership request at '
                        '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
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

    @permission_required('join', (Agora, 'id', 'agoraid'))
    def join_action(self, request, agora, **kwargs):
        '''
        Action that an user can execute to join an agora if it has permissions
        '''
        request.user.get_profile().add_to_agora(agora_id=agora.id, request=request)

        return self.create_response(request, dict(status="success"))

    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def accept_membership_action(self, request, agora, username, **kwargs):
        '''
        Accept a membership request from the given username user in an agora
        '''
        if not re.match("^[a-zA-Z0-9_]+$", username):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        user = get_object_or_404(User, username=username)

        # One can only accept membership if it can cancel it
        if not agora.has_perms('cancel_membership_request', user):
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        # remve the request membership status and add user to the agora
        remove_perm('requested_membership', user, agora)
        remove_perm('denied_requested_membership', user, agora)
        agora.members.add(user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='accepted membership request',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        profile = user.get_profile()
        vote_accepted = False

        if isinstance(profile.extra, dict) and 'pending_ballot_id' in profile.extra:
            pending_ballot_id = profile.extra['pending_ballot_id']
            status_str = 'pending_ballot_status_%d' % pending_ballot_id
            if status_str in profile.extra and profile.extra[status_str] == 'confirmed':
                vote = CastVote.objects.filter(id=profile.extra['pending_ballot_id'])
                if vote.count() > 0:
                    vote = vote[0]
                    # invalidate older votes from the same voter to the same election
                    old_votes = vote.election.cast_votes.filter(is_direct=True,
                        invalidated_at_date=None, voter=user)
                    for old_vote in old_votes:
                        if old_vote.id == vote.id:
                            continue
                        old_vote.invalidated_at_date = timezone.now()
                        old_vote.is_counted = False
                        old_vote.save()
                    vote.is_counted = True
                    vote.save()
                    vote_accepted = True
                    del profile.extra['pending_ballot_id']
                    del profile.extra[status_str]
                    profile.save()

        # Mail to the user
        if profile.has_perms('receive_email_updates'):
            translation.activate(profile.lang_code)
            context = get_base_email_context(request)

            if not vote_accepted:
                notif_txt = _('Your membership has been accepted at '
                        '%(agora)s. Congratulations!') % dict(
                            agora=agora.get_full_name()
                        )
            else:
                notif_txt = _('Your membership has been accepted at '
                        '%(agora)s and your ballot has been finally casted. Congratulations!') % dict(
                            agora=agora.get_full_name()
                        )
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=notif_txt,
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - you are now member of %(agora)s') % dict(
                            site=Site.objects.get_current().domain,
                            agora=agora.get_full_name()
                        ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        return self.create_response(request, dict(status="success"))

    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def deny_membership_action(self, request, agora, username, **kwargs):
        '''
        Deny a membership request from the given username user in an agora
        '''
        if not re.match("^[a-zA-Z0-9_]+$", username):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        user = get_object_or_404(User, username=username)

        # One can only accept membership if it can cancel it
        if not agora.has_perms('cancel_membership_request', user):
            raise ImmediateHttpResponse(response=http.HttpForbidden())


        # remove the request membership status
        remove_perm('requested_membership', user, agora)
        assign('denied_requested_membership', user, agora)
        return self.create_response(request, dict(status="success"))

    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def add_membership_action(self, request, agora, username, welcome_message, **kwargs):
        '''
        Adds a member (specified with username) to this agora, sending a
        welcome message to this new member via email
        '''
        if not re.match("^[a-zA-Z0-9-_]+$", username):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        user = get_object_or_404(User, username=username)

        # remve the request membership status and add user to the agora
        remove_perm('requested_membership', user, agora)
        agora.members.add(user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='added member',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            translation.activate(user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('As administrator of %(agora)s, %(user)s has '
                    'added you to this agora. You can remove your '
                    'membership at anytime, and if you think he is spamming '
                    'you please contact with this website '
                    'administrators.') % dict(
                        agora=agora.get_full_name(),
                        user=request.user.username
                    ) + '\n\n' + clean_html(welcome_message),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - Added as member to %(agora)s') % dict(
                    site=Site.objects.get_current().domain,
                    agora=agora.get_full_name()
                ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        return self.create_response(request, dict(status="success"))


    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def remove_membership_action(self, request, agora, username, goodbye_message, **kwargs):
        '''
        Remove a member (specified with username) from this agora, sending a
        goodbye message to this member via email
        '''
        if not re.match("^[a-zA-Z0-9_]+$", username):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        user = get_object_or_404(User, username=username)

        # user might not be allowed to leave (because he's the owner, or because
        # he's not a member of this agora at all)
        if not agora.has_perms('leave', user):
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        agora.members.remove(user)
        agora.save()


        # cancel user votes in active untallied elections in this agora
        # so that they don't count
        for e in agora.get_open_elections():
            for vote in CastVote.objects.filter(voter=user, election=e,
                is_counted=True, is_direct=True, invalidated_at_date=None):
                vote.is_counted = False
                vote.save()

        # create an action for the event
        action.send(request.user, verb='removed member',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            translation.activate(user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your membership of %(agora)s has been removed. '
                            'Sorry about that!') % dict(
                            agora=agora.get_full_name()
                        ) + '\n\n' + clean_html(goodbye_message),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - membership of %(agora)s removed') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        return self.create_response(request, dict(status="success"))


    @permission_required('request_admin_membership', (Agora, 'id', 'agoraid'))
    def request_admin_membership_action(self, request, agora, **kwargs):
        '''
        Requests membership from authenticated user to an agora
        '''
        assign('requested_admin_membership', request.user, agora)

        action.send(request.user, verb='requested admin membership', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        kwargs=dict(
            agora_id=agora.id,
            user_id=request.user.id,
            is_secure=request.is_secure(),
            site_id=Site.objects.get_current().id,
            remote_addr=request.META.get('REMOTE_ADDR')
        )
        send_request_admin_membership_mails.apply_async(kwargs=kwargs)

        return self.create_response(request, dict(status="success"))


    @permission_required('cancel_admin_membership_request', (Agora, 'id', 'agoraid'))
    def cancel_admin_membership_request_action(self, request, agora, **kwargs):
        '''
        Cancel an admin membership request from the given username user in an agora
        '''
        # remove the request membership status and add user to the agora
        remove_perm('requested_admin_membership', request.user, agora)

        # create an action for the event
        action.send(request.user, verb='canceled requested admin membership',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=request.user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            translation.activate(request.user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('You canceled your admin membership request at '
                    '%(agora)s') % dict(
                        agora=agora.get_full_name()
                    ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - canceled your admin membership request at '
                        '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
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

    @permission_required('leave', (Agora, 'id', 'agoraid'))
    def leave_action(self, request, agora, **kwargs):
        '''
        Remove a member (specified with username) from this agora, sending a
        goodbye message to this member via email
        '''
        agora.members.remove(request.user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='left',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # cancel user votes in active untallied elections in this agora
        # so that they don't count
        for e in agora.get_open_elections():
            for vote in CastVote.objects.filter(voter=request.user, election=e,
                is_counted=True, is_direct=True, invalidated_at_date=None):
                vote.is_counted = False
                vote.save()

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            translation.activate(request.user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('You have removed your membership '
                    'from %(agora)s') % dict(
                            agora=agora.get_full_name()
                        ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - membership removed from '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
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


    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def accept_admin_membership_action(self, request, agora, username, **kwargs):
        '''
        Accept an admin membership request from the given username user in an agora
        '''
        if not re.match("^[a-zA-Z0-9_]+$", username):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        user = get_object_or_404(User, username=username)

        # One can only accept membership if it can cancel it
        if not agora.has_perms('cancel_admin_membership_request', user):
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        # remve the request admin membership status and add user to the agora
        remove_perm('requested_admin_membership', user, agora)
        agora.admins.add(user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='accepted admin membership request',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            translation.activate(user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your admin membership has been accepted at '
                    '%(agora)s. Congratulations!') % dict(
                        agora=agora.get_full_name()
                    ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - you are now admin of %(agora)s') % dict(
                            site=Site.objects.get_current().domain,
                            agora=agora.get_full_name()
                        ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        return self.create_response(request, dict(status="success"))


    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def deny_admin_membership_action(self, request, agora, username, **kwargs):
        '''
        Deny an admin membership request from the given username user in an agora
        '''
        if not re.match("^[a-zA-Z0-9_]+$", username):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        user = get_object_or_404(User, username=username)

        # One can only accept admin membership if it can cancel it, which means
        # if it's requested
        if not agora.has_perms('cancel_admin_membership_request', user):
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        # remove the request admin membership status and add user to the agora
        remove_perm('requested_admin_membership', user, agora)

        # create an action for the event
        action.send(request.user, verb='denied admin membership request',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            translation.activate(user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your admin membership request at %(agora)s '
                    'has been denied. Sorry about that!') % dict(
                        agora=agora.get_full_name()
                    ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - admin membership request denied at '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        return self.create_response(request, dict(status="success"))


    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def add_admin_membership_action(self, request, agora, username, welcome_message, **kwargs):
        '''
        Adds an admin (specified with username) to this agora, sending a
        welcome message to this new admin via email
        '''
        if not re.match("^[a-zA-Z0-9_]+$", username):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        user = get_object_or_404(User, username=username)

        # remve the request admin membership status and add user to the agora
        remove_perm('requested_admin_membership', user, agora)
        agora.admins.add(user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='added admin',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            translation.activate(user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('As administrator of %(agora)s, %(user)s has '
                    'promoted you to admin of this agora. You can remove '
                    'your admin membership at anytime, and if you think he is '
                    'spamming you please contact with this website '
                    'administrators.') % dict(
                        agora=agora.get_full_name(),
                        user=request.user.username
                    ) + '\n\n' + clean_html(welcome_message),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - Promoted to admin of agora %(agora)s') % dict(
                    site=Site.objects.get_current().domain,
                    agora=agora.get_full_name()
                ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        return self.create_response(request, dict(status="success"))


    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def remove_admin_membership_action(self, request, agora, username, goodbye_message, **kwargs):
        '''
        Remove admin status in this agora to the specified user, sending a
        message to this member via email
        '''
        if not re.match("^[a-zA-Z0-9_]+$", username):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())
        user = get_object_or_404(User, username=username)

        # user might not be allowed to leave (because he's the owner, or because
        # he's not a member of this agora at all)
        if not agora.has_perms('leave_admin', user):
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        agora.admins.remove(user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='revoked admin permissions',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            target=user,
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if user.get_profile().has_perms('receive_email_updates'):
            translation.activate(user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('Your admin permissions on %(agora)s have been revoked. Sorry about that!') % dict(
                            agora=agora.get_full_name()
                        ) + '\n\n' + clean_html(goodbye_message),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - admin permissions revoked on '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
                    ),
                body=render_to_string('agora_core/emails/agora_notification.txt',
                    context),
                to=[user.email])

            email.attach_alternative(
                render_to_string('agora_core/emails/agora_notification.html',
                    context), "text/html")
            email.send()
            translation.deactivate()

        return self.create_response(request, dict(status="success"))

    @permission_required('leave_admin', (Agora, 'id', 'agoraid'))
    def leave_admin_action(self, request, agora, **kwargs):
        '''
        Remove a member (specified with username) from this agora, sending a
        goodbye message to this member via email
        '''
        agora.admins.remove(request.user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='gave up admin permissions',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            translation.activate(request.user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('You have given up your admin permissions '
                    'on %(agora)s') % dict(
                            agora=agora.get_full_name()
                        ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - admin permissions given up on '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
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


    @permission_required('create_election', (Agora, 'id', 'agoraid'))
    def create_election_action(self, request, agora, **kwargs):
        '''
        Form to create election
        '''
        return self.wrap_form(CreateElectionForm)(request, **kwargs)

    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def set_authorities_action(self, request, agora, authorities_ids, **kwargs):
        '''
        Form to create election
        '''
        from agora_site.agora_core.models import Authority

        # check input data
        error_data = dict(errors=_('Invalid authorities_ids.'))
        if not isinstance(authorities_ids, list):
            return self.raise_error(request, http.HttpBadRequest, error_data)

        if len(authorities_ids) < settings.MIN_NUM_AUTHORITIES or\
                len(authorities_ids) > settings.MAX_NUM_AUTHORITIES:
            error_data = dict(errors=_('Invalid number of authorities.'))
            return self.raise_error(request, http.HttpBadRequest, error_data)

        for i in authorities_ids:
            if not isinstance(i, int) or not Authority.objects.filter(pk=i).exists():
                return self.raise_error(request, http.HttpBadRequest, error_data)

        agora.agora_local_authorities = Authority.objects.filter(id__in=authorities_ids)
        agora.save()

        agora.request_new_delegation_election()

        # for each delegated vote, expire it, as authorities have changed
        for vote in agora.delegation_election.cast_votes\
                .filter(is_counted=True, invalidated_at_date=None):
            vote.invalidated_at_date = timezone.now()
            vote.is_counted = False
            vote.save()

        return self.create_response(request, dict(status="success"))

    @permission_required('delegate', (Agora, 'id', 'agoraid'))
    def delegate_vote_action(self, request, agora, **kwargs):
        '''
        Form to delegate the vote
        '''
        return self.wrap_form(DelegateVoteForm)(request, **kwargs)


    @permission_required('delegate', (Agora, 'id', 'agoraid'))
    def cancel_vote_delegation(self, request, agora, **kwargs):
        '''
        Cancel a delegated vote
        '''

        # get the delegated vote, if any
        vote = agora.get_delegated_vote_for_user(request.user)
        if not vote:
            data = dict(errors=_('Your vote is not currently delegated.'))
            return self.raise_error(request, http.HttpBadRequest, data)

        # invalidate the vote
        vote.invalidated_at_date = timezone.now()
        vote.is_counted = False
        vote.save()

        # create an action for the event
        action.send(request.user, verb='canceled vote delegation',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            translation.activate(request.user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('You have removed your vote delegation '
                    'from %(agora)s') % dict(
                            agora=agora.get_full_name()
                        ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - vote delegation removed from '
                    '%(agora)s') % dict(
                        site=Site.objects.get_current().domain,
                        agora=agora.get_full_name()
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

    def test_action(self, request, agora, param1=None, param2=None, **kwargs):
        '''
        In:
            param1 or param2
        '''

        if not (param1 or param2):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())

        return self.create_response(request, dict(status="success"))

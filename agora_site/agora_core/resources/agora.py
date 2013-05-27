import re
import datetime

from django.contrib.auth.models import User
from django.contrib import messages
from django.forms import ModelForm
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

from agora_site.agora_core.models import Agora
from agora_site.agora_core.tasks.agora import (send_request_membership_mails,
    send_request_admin_membership_mails, )
from agora_site.agora_core.resources.user import UserResource
from agora_site.agora_core.forms import PostCommentForm, CreateElectionForm
from agora_site.agora_core.forms.agora import DelegateVoteForm
from agora_site.agora_core.views import AgoraActionJoinView
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.misc.decorators import permission_required
from agora_site.misc.utils import (geolocate_ip, get_base_email_context)

ELECTION_RESOURCE = 'agora_site.agora_core.resources.election.ElectionResource'


class TinyAgoraResource(GenericResource):
    '''
    Tiny Resource representing agoras.

    Typically used to include the critical agora information in other
    resources, as in ActionResource for example.
    '''

    content_type = fields.CharField(default="agora")
    url = fields.CharField()
    full_name = fields.CharField()
    mugshot_url = fields.CharField()

    class Meta(GenericMeta):
        queryset = Agora.objects.all()
        fields = ['name', 'pretty_name', 'id', 'short_description']

    def dehydrate_url(self, bundle):
        return bundle.obj.get_link()

    def dehydrate_full_name(self, bundle):
        return bundle.obj.get_full_name()

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_mugshot_url()


class CreateAgoraForm(ModelForm):
    '''
    Form used to validate the user information in the
    agora creation.
    '''
    class Meta(GenericMeta):
        model = Agora
        fields = ('pretty_name', 'short_description', 'is_vote_secret')

class AgoraAdminForm(ModelForm):
    '''
    Form used to validate agora administration details.
    '''
    class Meta(GenericMeta):
        model = Agora
        fields = ('pretty_name', 'short_description', 'is_vote_secret',
            'biography', 'membership_policy', 'comments_policy')


class AgoraUserResource(UserResource):
    agora_permissions = fields.ApiField() # agora permissions
    agora = None
    request_user = None

    def dehydrate_agora_permissions(self, bundle):
        if not self.agora.has_perms('admin', self.request_user):
            if self.agora.has_perms('leave', self.request_user) and\
                self.agora.has_perms('receive_mail', bundle.obj):
                return ['receive_mail']
            else:
                return []

        return self.agora.get_perms(bundle.obj)

def user_resource_for_agora(agora, request_user):
    '''
    Generates a custom user resource that has an agora_permissions property
    listing the user permissions in the given agora, if the requesting user is
    an admin
    '''
    resource = AgoraUserResource()
    resource.agora = agora
    resource.request_user = request_user
    return resource

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
    creator = fields.ForeignKey(UserResource, 'creator', full=True)
    url = fields.CharField()
    full_name = fields.CharField()
    mugshot_url = fields.CharField()

    class Meta(GenericMeta):
        queryset = Agora.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'delete']
        validation = AgoraValidation()
        filtering = { "name": ALL, }

    def dehydrate_url(self, bundle):
        return bundle.obj.get_link()

    def dehydrate_full_name(self, bundle):
        return bundle.obj.get_full_name()

    def dehydrate_mugshot_url(self, bundle):
        return bundle.obj.get_mugshot_url()

    @permission_required('create', check_static=Agora)
    def obj_create(self, bundle, **kwargs):
        self.is_valid(bundle)
        if bundle.errors:
            raise ImmediateHttpResponse(response=self.error_response(
                bundle.request, bundle.errors))

        pretty_name = bundle.data['pretty_name']
        short_description = bundle.data['short_description']
        is_vote_secret = bundle.data['is_vote_secret']

        agora = Agora(pretty_name=pretty_name,
                      short_description=short_description,
                      is_vote_secret=is_vote_secret)
        agora.create_name(bundle.request.user)
        agora.creator = bundle.request.user
        agora.url = bundle.request.build_absolute_uri(agora.get_link())

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

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/admins%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_admin_list'), name="api_agora_admin_list"),

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/membership_requests%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_request_list'), name="api_agora_request_list"),

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

    def get_admin_list(self, request, **kwargs):
        '''
        List admin members of this agora
        '''
        return self.get_custom_resource_list(request,
            resourcefunc=user_resource_for_agora,
            queryfunc=lambda agora: agora.admins.all(), **kwargs)

    def get_member_list(self, request, **kwargs):
        '''
        List the members of this agora
        '''
        return self.get_custom_resource_list(request,
            resourcefunc=user_resource_for_agora,
            queryfunc=lambda agora: agora.members.all(), **kwargs)

    def get_active_delegates_list(self, request, **kwargs):
        '''
        List currently active delegates in this agora
        '''
        return self.get_custom_resource_list(request,
            resourcefunc=user_resource_for_agora,
            queryfunc=lambda agora: agora.active_delegates(), **kwargs)

    def get_all_elections_list(self, request, **kwargs):
        '''
        List all elections in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request, resource=ElectionResource,
            queryfunc=lambda agora: agora.all_elections(), **kwargs)

    def get_tallied_elections_list(self, request, **kwargs):
        '''
        List elections that have been already tallied in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request, resource=ElectionResource,
            queryfunc=lambda agora: agora.get_tallied_elections(), **kwargs)

    def get_open_elections_list(self, request, **kwargs):
        '''
        List the elections that are currently opened in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request, resource=ElectionResource,
            queryfunc=lambda agora: agora.get_open_elections(), **kwargs)

    def get_requested_elections_list(self, request, **kwargs):
        '''
        List the elections that are currently requested in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request, resource=ElectionResource,
            queryfunc=lambda agora: agora.requested_elections(), **kwargs)

    def get_archived_elections_list(self, request, **kwargs):
        '''
        List the elections that have been archived in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request, resource=ElectionResource,
            queryfunc=lambda agora: agora.archived_elections(), **kwargs)

    def get_approved_elections_list(self, request, **kwargs):
        '''
        List the elections that are currently opened in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request, resource=ElectionResource,
            queryfunc=lambda agora: agora.approved_elections(), **kwargs)

    def get_request_list(self, request, **kwargs):
        '''
        List agora membership requests
        '''

        def get_queryset(agora):
            from guardian.shortcuts import get_users_with_perms
            users = get_users_with_perms(agora, attach_perms=True)
            users = [k.username for k, v in users.items() if "requested_membership" in v]
            queryset = User.objects.filter(username__in=users)
            return queryset

        return self.get_custom_resource_list(request, queryfunc=get_queryset,
            resourcefunc=user_resource_for_agora, **kwargs)

    @permission_required('admin', (Agora, 'id', 'agoraid'))
    def get_admin_request_list(self, request, **kwargs):
        '''
        List agora admin membership requests
        '''

        def get_queryset(agora):
            from guardian.shortcuts import get_users_with_perms
            users = get_users_with_perms(agora, attach_perms=True)
            users = [k.username for k, v in users.items() if "requested_admin_membership" in v]
            queryset = User.objects.filter(username__in=users)
            return queryset

        return self.get_custom_resource_list(request, queryfunc=get_queryset,
            resourcefunc=user_resource_for_agora, **kwargs)

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

            TODO
            * approve_election
            * deny_election
        '''

        actions = {
            'get_permissions': self.get_permissions_action,
            'test': self.test_action,

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
        return self.create_response(request,
            dict(permissions=agora.get_perms(request.user)))

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
        action.send(request.user, verb='cancelled requested membership',
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
                notification_text=_('Your cancelled your membership request at '
                    '%(agora)s') % dict(
                        agora=agora.get_full_name()
                    ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - cancelled your membership request at '
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
        agora.members.add(request.user)
        agora.save()

        action.send(request.user, verb='joined', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        if not is_following(request.user, agora):
            follow(request.user, agora, actor_only=False, request=request)

        # Mail to the user
        user = request.user
        if user.get_profile().has_perms('receive_email_updates'):
            translation.activate(user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('You just joined %(agora)s. '
                    'Congratulations!') % dict(agora=agora.get_full_name()),
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
        agora.members.add(user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='accepted membership request',
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
                notification_text=_('Your membership has been accepted at '
                    '%(agora)s. Congratulations!') % dict(
                        agora=agora.get_full_name()
                    ),
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

        # remove the request membership status and add user to the agora
        remove_perm('requested_membership', user, agora)

        # create an action for the event
        action.send(request.user, verb='denied membership request',
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
                notification_text=_('Your membership request at %(agora)s '
                    'has been denied. Sorry about that!') % dict(
                        agora=agora.get_full_name()
                    ),
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - membership request denied at '
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
    def add_membership_action(self, request, agora, username, welcome_message, **kwargs):
        '''
        Adds a member (specified with username) to this agora, sending a
        welcome message to this new member via email
        '''
        if not re.match("^[a-zA-Z0-9_]+$", username):
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
                    'himself added you to this agora. You can remove your '
                    'membership at anytime, and if you think he is spamming '
                    'you please contact with this website '
                    'administrators.\n\n') % dict(
                        agora=agora.get_full_name(),
                        user=request.user.username
                    ) + welcome_message,
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
                notification_text=_('Your have been removed from membership '
                    'from %(agora)s . Sorry about that!\n\n') % dict(
                            agora=agora.get_full_name()
                        ) + goodbye_message,
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - membership removed from '
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
        action.send(request.user, verb='cancelled requested admin membership',
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
                notification_text=_('Your cancelled your admin membership request at '
                    '%(agora)s') % dict(
                        agora=agora.get_full_name()
                    ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - cancelled your admin membership request at '
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
                    'himself promoted you to admin of this agora. You can remove '
                    'your admin membership at anytime, and if you think he is '
                    'spamming you please contact with this website '
                    'administrators.\n\n') % dict(
                        agora=agora.get_full_name(),
                        user=request.user.username
                    ) + welcome_message,
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
        action.send(request.user, verb='removed admin permissions',
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
                notification_text=_('Your have been removed admin permissions '
                    'from %(agora)s . Sorry about that!\n\n') % dict(
                            agora=agora.get_full_name()
                        ) + goodbye_message,
                to=user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - admin permissions removed from '
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
        action.send(request.user, verb='left admin permissions',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            translation.activate(request.user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('Your hav removed your admin permissions '
                    'from %(agora)s') % dict(
                            agora=agora.get_full_name()
                        ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - admin permissions removed from '
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
        action.send(request.user, verb='cancelled vote delegation',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            translation.activate(request.user.get_profile().lang_code)
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('Your hav removed your vote delegation '
                    'from %(agora)s') % dict(
                            agora=agora.get_full_name()
                        ),
                to=request.user
            ))

            email = EmailMultiAlternatives(
                subject=_('%(site)s - admin permissions removed from '
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

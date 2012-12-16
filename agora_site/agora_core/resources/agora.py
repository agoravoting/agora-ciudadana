import re

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
from agora_site.agora_core.tasks.agora import send_request_membership_mails
from agora_site.agora_core.resources.user import UserResource
from agora_site.agora_core.forms import PostCommentForm
from agora_site.agora_core.views import AgoraActionJoinView
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.misc.decorators import permission_required
from agora_site.misc.utils import geolocate_ip, get_base_email_context

ELECTION_RESOURCE = 'agora_site.agora_core.resources.election.ElectionResource'


class CreateAgoraForm(ModelForm):
    class Meta:
        model = Agora
        fields = ('pretty_name', 'short_description', 'is_vote_secret')

class AgoraAdminForm(ModelForm):
    class Meta:
        model = Agora
        fields = ('pretty_name', 'short_description', 'is_vote_secret',
            'biography', 'membership_policy', 'comments_policy')


class AgoraValidation(Validation):
    def is_valid(self, bundle, request=None):
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
    creator = fields.ForeignKey(UserResource, 'creator', full=True)

    class Meta(GenericMeta):
        queryset = Agora.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'delete']
        validation = AgoraValidation()
        filtering = { "name": ALL, }

    @permission_required('create', check_static=Agora)
    def obj_create(self, bundle, request=None, **kwargs):
        pretty_name = bundle.data['pretty_name']
        short_description = bundle.data['short_description']
        is_vote_secret = bundle.data['is_vote_secret']

        agora = Agora(pretty_name=pretty_name,
                      short_description=short_description,
                      is_vote_secret=is_vote_secret)
        agora.create_name(request.user)
        agora.creator = request.user
        agora.url = request.build_absolute_uri(reverse('agora-view',
            kwargs=dict(username=agora.creator.username, agoraname=agora.name)))

        # we need to save before add members
        agora.save()

        agora.members.add(request.user)
        agora.admins.add(request.user)

        bundle = self.build_bundle(obj=agora, request=request)
        bundle = self.full_dehydrate(bundle)
        return bundle

    @permission_required('delete', (Agora, 'id', 'pk'))
    def obj_delete(self, request=None, **kwargs):
        return super(AgoraResource, self).obj_delete(request, **kwargs)

    @permission_required('admin', (Agora, 'id', 'pk'))
    def obj_update(self, bundle, request=None, **kwargs):
        agora = Agora.objects.get(**kwargs)
        for k, v in bundle.data.items():
            setattr(agora, k, v)
        agora.save()

        bundle = self.build_bundle(obj=agora, request=request)
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

            url(r"^(?P<resource_name>%s)/(?P<agora>\d+)/add_comment%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('add_comment'), name="api_agora_add_comment"),
        ]

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
            url_name="api_agora_admin_list",
            queryfunc=lambda agora: agora.admins.all(), resource=UserResource,
            **kwargs)

    def get_member_list(self, request, **kwargs):
        '''
        List the members of this agora
        '''
        return self.get_custom_resource_list(request, url_name="api_agora_member_list",
            queryfunc=lambda agora: agora.members.all(), resource=UserResource,
            **kwargs)

    def get_active_delegates_list(self, request, **kwargs):
        '''
        List currently active delegates in this agora
        '''
        return self.get_custom_resource_list(request,
            url_name="api_agora_active_delegate_list",
            queryfunc=lambda agora: agora.active_delegates(), resource=UserResource,
            **kwargs)

    def get_all_elections_list(self, request, **kwargs):
        '''
        List all elections in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request,
            url_name="api_agora_all_elections_list",
            queryfunc=lambda agora: agora.all_elections(), resource=ElectionResource,
            **kwargs)

    def get_tallied_elections_list(self, request, **kwargs):
        '''
        List elections that have been already tallied in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request,
            url_name="api_agora_tallied_elections_list",
            queryfunc=lambda agora: agora.get_tallied_elections(),
            resource=ElectionResource, **kwargs)

    def get_open_elections_list(self, request, **kwargs):
        '''
        List the elections that are currently opened in an agora
        '''
        from agora_site.agora_core.resources.election import ElectionResource
        return self.get_custom_resource_list(request,
            url_name="api_agora_open_elections_list",
            queryfunc=lambda agora: agora.get_open_elections(),
            resource=ElectionResource, **kwargs)

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

        return self.get_custom_resource_list(request,queryfunc=get_queryset,
            url_name="api_agora_request_list", resource=UserResource, **kwargs)

    def get_custom_resource_list(self, request, url_name, queryfunc, resource, **kwargs):
        '''
        List users
        '''
        agora = None
        agoraid = kwargs.get('agoraid', -1)
        try:
            agora = Agora.objects.get(id=agoraid)
        except:
            raise ImmediateHttpResponse(response=http.HttpNotFound())

        url_args = dict(
            resource_name=self._meta.resource_name,
            api_name=self._meta.api_name,
            agoraid=agoraid
        )
        list_url  = self._build_reverse_url(url_name, kwargs=url_args)

        return resource().get_custom_list(request=request, kwargs=kwargs,
            list_url=list_url, queryset=queryfunc(agora))

    def action(self, request, **kwargs):
        '''
        Requests an action on this agora

        actions:
            DONE
            * get_permissions

            * request_membership
            * join
            * leave
            * accept_membership
            * deny_membership
            * add_membership
            * remove_membership

            TODO

            * request_admin_membership
            * accept_admin_membership
            * deny_admin_membership
            * add_admin_membership
            * remove_admin_membership
            * leave_admin_membership

            * archive_agora
        '''

        actions = {
            'get_permissions': self.get_permissions_action,
            'test': self.test_action,

            'request_membership': self.request_membership_action,
            'join': self.join_action,
            'leave': self.leave_action,
            'accept_membership': self.accept_membership_action,
            'deny_membership': self.deny_membership_action,
            'add_membership': self.add_membership_action,
            'remove_membership': self.remove_membership_action,
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
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=user,
                notification_text=_('As administrator of %(agora)s, %(user)s has '
                    'added himself to you to this agora. You can remove your '
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

        return self.create_response(request, dict(status="success"))

    def leave_action(self, request, agora, **kwargs):
        '''
        Remove a member (specified with username) from this agora, sending a
        goodbye message to this member via email
        '''

        # user might not be allowed to leave (because he's the owner, or because
        # he's not a member of this agora at all)
        if not agora.has_perms('leave', request.user):
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        agora.members.remove(request.user)
        agora.save()

        # create an action for the event
        action.send(request.user, verb='left',
            action_object=agora, ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        # Mail to the user
        if request.user.get_profile().has_perms('receive_email_updates'):
            context = get_base_email_context(request)
            context.update(dict(
                agora=agora,
                other_user=request.user,
                notification_text=_('Your have removed your membership '
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

        return self.create_response(request, dict(status="success"))

    def test_action(self, request, agora, param1=None, param2=None, **kwargs):
        '''
        In:
            param1 or param2
        '''

        if not (param1 or param2):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())

        return self.create_response(request, dict(status="success"))

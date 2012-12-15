from django.contrib.auth.models import User
from django.contrib import messages
from django.forms import ModelForm
from django.core.urlresolvers import reverse
from django.conf.urls.defaults import url
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives, EmailMessage, send_mass_mail
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

from guardian.shortcuts import assign

from agora_site.agora_core.models import Agora
from agora_site.agora_core.tasks.agora import send_request_membership_mails
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource
from agora_site.misc.decorators import permission_required

from agora_site.agora_core.views import AgoraActionJoinView
from agora_site.misc.utils import geolocate_ip

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

            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/requests%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_request_list'), name="api_agora_resquest_list"),
        ]

    def get_admin_list(self, request, **kwargs):
        return self.get_user_list(request, url_name="api_agora_admin_list",
            queryfunc=lambda agora: agora.admins.all(), **kwargs)

    def get_member_list(self, request, **kwargs):
        return self.get_user_list(request, url_name="api_agora_member_list",
            queryfunc=lambda agora: agora.members.all(), **kwargs)

    def get_user_list(self, request, url_name, queryfunc, **kwargs):
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

        return UserResource().get_custom_list(request=request, kwargs=kwargs,
            list_url=list_url, queryset=queryfunc(agora))

    def get_request_list(self, request, **kwargs):
        '''
        List agora membership requests
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
        list_url  = self._build_reverse_url( "api_agora_resquest_list",
            kwargs=url_args)

        from guardian.shortcuts import get_users_with_perms

        users = get_users_with_perms(agora, attach_perms=True)
        users = [k.username for k, v in users.items() if "requested_membership" in v]

        queryset = User.objects.filter(username__in=users)

        return UserResource().get_custom_list(request=request, kwargs=kwargs,
            list_url=list_url, queryset=queryset)

    def action(self, request, **kwargs):
        '''
        Requests an action on this agora

        actions:
            DONE
            * request_membership
            * join
            TODO
            * get_permissions
            * accept_membership
            * deny_membership
            * add_membership
            * remove_membership
            * archive_agora
        '''

        actions = {
            'request_membership': self.request_membership_action,
            'join': self.join_action,
            'test': self.test_action,
        }

        if request.method != "POST":
            raise ImmediateHttpResponse(response=http.HttpResponseNotAllowed())

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

        messages.add_message(request, messages.SUCCESS, _('You requested '
            'membership in %(agora)s. Soon the admins of this agora will '
            'decide on your request.') % dict(agora=agora.get_link()))

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
        Requests membership from authenticated user to an agora
        '''
        agora.members.add(request.user)
        agora.save()

        action.send(request.user, verb='joined', action_object=agora,
            ipaddr=request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(request.META.get('REMOTE_ADDR'))))

        messages.add_message(request, messages.SUCCESS, _('You joined '
            '%(agora)s. Now you could take a look at what elections are '
            'available at this agora') % dict(agora=agora.get_link()))

        if not is_following(request.user, agora):
            follow(request.user, agora, actor_only=False, request=request)

        return self.create_response(request, dict(status="success"))

    def test_action(self, request, agora, param1=None, param2=None, **kwargs):
        '''
        In:
            param1 or param2
        '''

        if not (param1 or param2):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())

        return self.create_response(request, dict(status="success"))


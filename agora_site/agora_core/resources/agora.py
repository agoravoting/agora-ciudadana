from django.forms import ModelForm
from django.core.urlresolvers import reverse
from django.conf.urls.defaults import url

from tastypie import fields
from tastypie.validation import Validation, CleanedDataFormValidation
from tastypie.utils import trailing_slash
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.constants import ALL

from agora_site.agora_core.models import Agora
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource
from agora_site.misc.decorators import permission_required

from agora_site.agora_core.views import AgoraActionJoinView

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

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<agoraid>\d+)/action%s$" \
                % (self._meta.resource_name, trailing_slash()),
                self.wrap_view('action'), name="api_agora_action"),
            ]

    def action(self, request, **kwargs):
        '''
        Requests an action on this agora

        actions:
            DONE
            * request_membership
            TODO
            * accept_membership
            * deny_membership
            * add_membership
            * remove_membership
            * archive_agora
        '''

        actions = {
            'request_membership': self.request_membership_action,
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

    def request_membership_action(self, request, agora, **kwargs):
        '''
        Requests membership from authenticated user to an agora
        '''

        view = AgoraActionJoinView()
        view.request = request
        ret = view.post(request, agora.creator.username, agora.name)

        return self.create_response(request, dict(status="success"))

    def test_action(self, request, agora, param1=None, param2=None, **kwargs):
        '''
        In:
            param1 or param2
        '''

        if not (param1 or param2):
            raise ImmediateHttpResponse(response=http.HttpBadRequest())

        return self.create_response(request, dict(status="success"))

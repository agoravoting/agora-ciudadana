from django.forms import ModelForm
from django.core.urlresolvers import reverse

from tastypie import fields
from tastypie.validation import Validation, CleanedDataFormValidation

from agora_site.agora_core.models import Agora
from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.resources.user import UserResource
from agora_site.misc.decorators import permission_required

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

    def obj_update(self, bundle, request=None, **kwargs):
        agora = Agora.objects.get(**kwargs)
        for k, v in bundle.data.items():
            setattr(agora, k, v)
        agora.save()

        bundle = self.build_bundle(obj=agora, request=request)
        bundle = self.full_dehydrate(bundle)
        return bundle

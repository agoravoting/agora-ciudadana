from django.contrib.auth.models import User

from agora_site.misc.generic_resource import GenericResource, GenericMeta


class UserResource(GenericResource):
    class Meta(GenericMeta):
        queryset = User.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

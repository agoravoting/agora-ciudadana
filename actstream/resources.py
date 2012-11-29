from agora_site.misc.generic_resource import GenericResource, GenericMeta

from actstream.models import Follow, Action


class FollowResource(GenericResource):
    class Meta(GenericMeta):
        queryset = Follow.objects.all()



class ActionResource(GenericResource):
    class Meta(GenericMeta):
        queryset = Action.objects.all()

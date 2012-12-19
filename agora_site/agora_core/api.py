from tastypie.api import Api
from resources.user import UserResource
from resources.agora import AgoraResource
from resources.election import ElectionResource
from resources.castvote import CastVoteResource
from resources.search import SearchResource
from actstream.resources import FollowResource, ActionResource

v1 = Api("v1")
v1.register(UserResource())
v1.register(AgoraResource())
v1.register(ElectionResource())
v1.register(CastVoteResource())
v1.register(FollowResource())
v1.register(ActionResource())
v1.register(SearchResource())

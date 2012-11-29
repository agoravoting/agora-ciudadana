from tastypie.api import Api
from resources.user import UserResource
from resources.agora import AgoraResource
from resources.election import ElectionResource

v1 = Api("v1")
v1.register(UserResource())
v1.register(AgoraResource())
v1.register(ElectionResource())

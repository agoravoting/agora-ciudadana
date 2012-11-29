from tastypie.api import Api
from resources.user import UserResource
from resources.agora import AgoraResource

v1 = Api("v1")
v1.register(UserResource())
v1.register(AgoraResource())

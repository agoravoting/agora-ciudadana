from tastypie.api import Api
from resources.user import UserResource

v1 = Api("v1")
v1.register(UserResource())

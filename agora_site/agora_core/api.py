from tastypie.api import Api
from resources import UserResource

v1 = Api("v1")
v1.register(UserResource())

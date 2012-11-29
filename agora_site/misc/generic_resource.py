from tastypie.authorization import Authorization
from tastypie.resources import ModelResource
from tastypie import fields


class GenericResource(ModelResource):
    def determine_format(self, request):
        """
           Necessary to avoid the format=json
           attribute in the urli
        """
        return 'application/json'


class GenericMeta:
    list_allowed_methods = ['get', 'post']
    detail_allowed_methods = ['get', 'post', 'put', 'delete']
    # TODO When we have the first version of the API we could
    # work in the Authorization
    # authorization = DjangoAuthorization()
    authorization = Authorization()
    #authentication = SessionAuthentication()
    always_return_data = True
    include_resource_uri = False

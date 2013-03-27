
from simplejson.decoder import JSONDecodeError

from django.conf import settings
from django.core.paginator import InvalidPage
from django.http import Http404

from django.template import RequestContext
from django.utils import simplejson
from django.views.decorators.csrf import csrf_exempt

from tastypie.authorization import Authorization
from tastypie.authentication import (ApiKeyAuthentication, MultiAuthentication,
                                     SessionAuthentication)
from tastypie.resources import ModelResource
from tastypie.paginator import Paginator
from tastypie import fields, http
from tastypie.exceptions import NotFound, BadRequest, InvalidFilterError, HydrationError, InvalidSortError, ImmediateHttpResponse, HttpResponse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from tastypie.utils.mime import build_content_type


class GenericResourceMixin:

    def deserialize_post_data(self, request):
        '''
        Useful for get deserialized data
        '''
        return self.deserialize(request,
                                request.raw_post_data,
                                format=request.META.get('CONTENT_TYPE', 'application/json'))

    def determine_format(self, request):
        """
        Necessary to avoid the format=json attribute in the urli
        """
        return 'application/json'

    def raise_error(self, request, http_method, data):
        '''
        Shortcut to return an error
        '''
        desired_format = self.determine_format(request)
        serialized = self.serialize(request, data, desired_format)
        return http_method(serialized,
            content_type=build_content_type(desired_format))

    def wrap_form(self, form_class, method="POST"):
        """
        Creates a view for a given form class, which calls to is_valid()
        and save() when needed. You can get the form args reimplementing
        static_get_form_kwargs(request, data, *args, **kwargs) in your
        form.
        """
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            try:
                desired_format = self.determine_format(request)
                if method == "POST":
                    data = self.deserialize(request, request.raw_post_data,
                        desired_format)
                elif method == "GET":
                    data = request.GET
                response_data = {}
                if hasattr(form_class, "static_get_form_kwargs"):
                    kwargs = form_class.static_get_form_kwargs(request, data, 
                        *args, **kwargs)
                    form = form_class(**kwargs)
                else:
                    form = form_class(data=data)

                if not form.is_valid():
                    context = RequestContext(request, {})
                    context['form'] = form
                    errors = dict([(k, form.error_class.as_text(v)) for k, v in form.errors.items()])
                    response_data['errors'] = errors

                    serialized = self.serialize(request, response_data, desired_format)
                    return http.HttpBadRequest(serialized,
                        content_type=build_content_type(desired_format))

                else:
                    if hasattr(form, "save"):
                        obj = form.save()
                        if obj:
                            if hasattr(form, "bundle_obj"):
                                response_data = form.bundle_obj(obj, request)
                            else:
                                response_data = obj

                return self.create_response(request, response_data)
            except JSONDecodeError, e:
                data = dict(errors=e.message)
                serialized = self.serialize(request, data, desired_format)
                return http.HttpBadRequest(serialized,
                        content_type=build_content_type(desired_format))
            except (BadRequest, fields.ApiFieldError), e:
                data = dict(errors=e.args[0])
                serialized = self.serialize(request, data, desired_format)
                return http.HttpBadRequest(serialized,
                        content_type=build_content_type(desired_format))
            except ValidationError, e:
                data = dict(errors=', '.join(e.messages))
                serialized = self.serialize(request, data, desired_format)
                return http.HttpBadRequest(serialized,
                        content_type=build_content_type(desired_format))
            except Exception, e:
                if hasattr(e, 'response'):
                    return e.response

                # A real, non-expected exception.
                # Handle the case where the full traceback is more helpful
                # than the serialized error.
                if settings.DEBUG and getattr(settings, 'TASTYPIE_FULL_DEBUG', False):
                    raise

                # Re-raise the error to get a proper traceback when the error
                # happend during a test case
                if request.META.get('SERVER_NAME') == 'testserver':
                    raise

                # Rather than re-raising, we're going to things similar to
                # what Django does. The difference is returning a serialized
                # error message.
                return self._handle_500(request, e)

        return wrapper

    def get_custom_list(self, request, queryset):
        '''
        Generic function to paginate a queryset with a set of items per page.
        '''
        self.method_check(request, allowed=['get'])
        self.throttle_check(request)

        # Do the query.
        offset = int(request.GET.get('offset', 0))
        limit = min(int(request.GET.get('limit', 20)), 1000)
        paginator = Paginator(request.GET, queryset)

        try:
            object_list = paginator.get_slice(limit, offset)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []

        for result in object_list:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)

        page = {
            "meta": {
                "limit": limit,
                "offset": offset,
                "total_count": queryset.count()
            },
            'objects': objects,
        }

        self.log_throttled_access(request)
        return self.create_response(request, page)

class GenericResource(ModelResource, GenericResourceMixin):
    pass

from tastypie.authentication import Authentication
class ReadOnlyAuthentication(Authentication):
    '''
    Authenticates everyone if the request is GET 
    '''

    def is_authenticated(self, request, **kwargs):
        if request.method == 'GET':
            return True
        return False



class GenericMeta:
    list_allowed_methods = ['get', 'post']
    detail_allowed_methods = ['get', 'post', 'put', 'delete']
    authorization = Authorization()
    authentication = MultiAuthentication(ReadOnlyAuthentication(),
        SessionAuthentication(), ApiKeyAuthentication())
    always_return_data = True
    include_resource_uri = False


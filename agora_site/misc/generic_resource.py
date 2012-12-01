from tastypie.authorization import Authorization
from tastypie.resources import ModelResource
from tastypie import fields, http
from tastypie.exceptions import NotFound, BadRequest, InvalidFilterError, HydrationError, InvalidSortError, ImmediateHttpResponse, HttpResponse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from django.conf import settings

from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from django.utils import simplejson

class GenericResource(ModelResource):
    def determine_format(self, request):
        """
           Necessary to avoid the format=json attribute in the urli
        """
        return 'application/json'

    def wrap_form(self, form_class, method="POST"):
        """
            Creates a view for a given form class, which calls to is_valid() 
             and save() when needed
        """
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            try:
                if method == "POST":
                    data = request.POST
                elif method == "GET":
                    data = request.GET
                response_data = {}
                form = form_class(data=data)
                form.request = request
                response_class= HttpResponse

                if not form.is_valid():
                    context = RequestContext(request, {})
                    context['form'] = form
                    errors = dict([(k, form.error_class.as_text(v)) for k, v in form.errors.items()])
                    response_data['errors'] = errors

                    desired_format = self.determine_format(request)
                    serialized = self.serialize(request, response_data, desired_format)
                    return http.HttpBadRequest(serialized)

                else:
                    if hasattr(form, "save"):
                        form.save()

                # Our response can vary based on a number of factors, use
                # the cache class to determine what we should ``Vary`` on so
                # caches won't return the wrong (cached) version.
                varies = getattr(self._meta.cache, "varies", [])

                if varies:
                    patch_vary_headers(response, varies)

                if hasattr(self._meta.cache, "cacheable") and self._meta.cache.cacheable(request, response):
                    if self._meta.cache.cache_control():
                        # If the request is cacheable and we have a
                        # ``Cache-Control`` available then patch the header.
                        patch_cache_control(response, **self._meta.cache.cache_control())

                if request.is_ajax() and not response.has_header("Cache-Control"):
                    # IE excessively caches XMLHttpRequests, so we're disabling
                    # the browser cache here.
                    # See http://www.enhanceie.com/ie/bugs.asp for details.
                    patch_cache_control(response, no_cache=True)

                return self.create_response(request, response_data,
                    response_class)
            except (BadRequest, fields.ApiFieldError), e:
                return http.HttpBadRequest(e.args[0])
            except ValidationError, e:
                return http.HttpBadRequest(', '.join(e.messages))
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


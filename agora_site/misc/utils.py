"""
taken from

http://www.djangosnippets.org/snippets/377/
"""

from django.core.urlresolvers import resolve, Resolver404
from django.http import HttpRequest
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.utils.datastructures import DictWrapper
from django.utils import datetime_safe
from django.core import mail as django_mail
from django.core.mail import (EmailMultiAlternatives, EmailMessage, send_mail,
    send_mass_mail, get_connection)
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import signals
from django.utils import simplejson as json
from django.views.generic import CreateView
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import _get_queryset
from django.forms.fields import Field, DateTimeField
from django.forms.util import ValidationError

import datetime
import pygeoip

from jsonfield import JSONField as JSONField2
from tastypie.fields import ApiField
from tastypie.serializers import Serializer

from guardian.core import ObjectPermissionChecker
from guardian.models import UserObjectPermission, GroupObjectPermission
from guardian.utils import get_identity


class FormRequestMixin(object):
    '''
    Adds self.request to the form constructor arguments
    '''
    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instanciating the form.
        """
        kwargs = super(FormRequestMixin, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

class RequestCreateView(FormRequestMixin, CreateView):
    pass

class JSONApiField(ApiField):
    '''
    Json Tastypie api field.
    '''
    dehydrated_type = 'dict'
    help_text = "JSON data. Ex: {'prices': [26.73, 34], 'name': 'Daniel'}"

    def dehydrate(self, bundle):
        if self.attribute and hasattr(bundle.obj, self.attribute):
            return getattr(bundle.obj, self.attribute)
        else:
            return None


class JSONFormField(Field):
    def clean(self, value):

        if not value and not self.required:
            return None

        value = super(JSONFormField, self).clean(value)

        if isinstance(value, basestring):
            try:
                json.loads(value)
            except ValueError:
                raise ValidationError(_("Enter valid JSON"))
        return value

class ISODateTimeFormField(DateTimeField):
    def strptime(self, value, format):
        from dateutil.parser import parse
        return parse(value)

class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.

    deserialization_params added on 2011-01-09 to provide additional hints at deserialization time
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def __init__(self, name=None, json_type=None, deserialization_params=None, **kwargs):
        self.json_type = json_type
        self.deserialization_params = deserialization_params
        super(JSONField, self).__init__(name, **kwargs)

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""
        if self.json_type:
            if isinstance(value, self.json_type):
                return value

        if isinstance(value, dict) or isinstance(value, list):
            return value

        if (type(value)==unicode and len(value.strip()) == 0) or value == None:
            return None

        try:
            parsed_value = json.loads(value)
        except:
            return None

        if self.json_type and parsed_value:
            parsed_value = self.json_type.fromJSONDict(parsed_value, **self.deserialization_params)

        return parsed_value

    # we should never look up by JSON field anyways.
    # def get_prep_lookup(self, lookup_type, value)

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""
        if isinstance(value, basestring):
            return value

        if value == None:
            return None

        if self.json_type and isinstance(value, self.json_type):
            the_dict = value.toJSONDict()
        else:
            the_dict = value

        return json.dumps(the_dict, cls=DjangoJSONEncoder)

    def get_internal_type(self):
        return 'JSONField'

    def db_type(self, connection):
        """
        Returns the database column data type for this field, for the provided
        connection.
        """
        # The default implementation of this method looks at the
        # backend-specific DATA_TYPES dictionary, looking up the field by its
        # "internal type".
        #
        # A Field class can implement the get_internal_type() method to specify
        # which *preexisting* Django Field class it's most similar to -- i.e.,
        # a custom field might be represented by a TEXT column type, which is
        # the same as the TextField Django field type, which means the custom
        # field's get_internal_type() returns 'TextField'.
        #
        # But the limitation of the get_internal_type() / data_types approach
        # is that it cannot handle database column types that aren't already
        # mapped to one of the built-in Django field types. In this case, you
        # can implement db_type() instead of get_internal_type() to specify
        # exactly which wacky database column type you want to use.
        data = DictWrapper(self.__dict__, connection.ops.quote_name, "qn_")
        real_internal_type = super(JSONField, self).get_internal_type()
        try:
            return (connection.creation.data_types[real_internal_type]
                    % data)
        except KeyError:
            return None

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)


##
## for schema migration, we have to tell South about JSONField
## basically that it's the same as its parent class
##
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^agora_site\.misc\.utils\.JSONField"])

GEOIP = None

def geolocate_ip(ip_addr):
    '''
    Given an ip address, geolocates it, returning a tuple(latitude, longitude)
    '''
    global GEOIP

    try:
        if not GEOIP:
            GEOIP = pygeoip.GeoIP(settings.GEOIP_DB_PATH)
        data = GEOIP.record_by_addr(ip_addr)
        return [data["latitude"], data["longitude"]]
    except Exception, e:
        return [0, 0]

def get_protocol(request):
    '''
    Given the request object, returns either 'https' or 'http' appropiately
    '''
    if request.is_secure():
        return 'https'
    else:
        return 'http'

def get_base_email_context(request):
    '''
    Returns a basic email context
    '''
    return dict(
            cancel_emails_url=reverse('cancel-email-updates'),
            site=Site.objects.get_current(),
            protocol=get_protocol(request)
        )


def get_base_email_context_task(is_secure, site_id):
    '''
    Returns a basic email context for tasks
    '''
    return dict(
            cancel_emails_url=reverse('cancel-email-updates'),
            site=Site.objects.get(pk=site_id),
            protocol=is_secure and 'https' or 'http'
        )

def send_mass_html_mail(datatuple, fail_silently=True, user=None, password=None,
                        connection=None):
    """
    Given a datatuple of (subject, text_content, html_content, from_email,
    recipient_list), sends each message to each recipient list. Returns the
    number of emails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    """
    connection = connection or get_connection(
        username=user, password=password, fail_silently=fail_silently
    )

    messages = []
    for subject, text, html, from_email, recipient in datatuple:
        message = EmailMultiAlternatives(subject, text, from_email, recipient)
        message.attach_alternative(html, 'text/html')
        messages.append(message)

    return connection.send_messages(messages)


def get_users_with_perm(obj, perm_codename):
    ctype = ContentType.objects.get_for_model(obj)
    qset = Q(
        userobjectpermission__content_type=ctype,
        userobjectpermission__object_pk=obj.pk,
        userobjectpermission__permission__codename=perm_codename,
        userobjectpermission__permission__content_type=ctype,)
    return User.objects.filter(qset).distinct()

def list_contains_all(l1, l2):
    '''
    return True if l2 contains all the elements in l1, False otherwise
    '''
    for el in l1:
        if el not in l2:
            return False
    return True

from functools import partial
from tastypie import fields
from tastypie.resources import Resource
from tastypie.exceptions import ApiFieldError
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from tastypie.contrib.contenttypes.resources import GenericResource


class GenericForeignKeyField(fields.ToOneField):
    """
    Provides access to GenericForeignKey objects from the django content_types
    framework.
    """

    def __init__(self, to, attribute, **kwargs):
        if not isinstance(to, dict):
            raise ValueError('to field must be a dictionary in GenericForeignKeyField')

        if len(to) <= 0:
            raise ValueError('to field must have some values')

        for k, v in to.iteritems():
            if not issubclass(k, models.Model) or not issubclass(v, Resource):
                raise ValueError('to field must map django models to tastypie resources')

        super(GenericForeignKeyField, self).__init__(to, attribute, **kwargs)

    def get_related_resource(self, related_instance):
        self._to_class = self.to.get(type(related_instance), None)

        if self._to_class is None and not self.null:
            raise TypeError('no resource for model %s' % type(related_instance))

        return super(GenericForeignKeyField, self).get_related_resource(related_instance)

    @property
    def to_class(self):
        if self._to_class and not issubclass(GenericResource, self._to_class):
            return self._to_class

        return partial(GenericResource, resources=self.to.values())

    def resource_from_uri(self, fk_resource, uri, request=None, related_obj=None, related_name=None):
        try:
            obj = fk_resource.get_via_uri(uri, request=request)
            fk_resource = self.get_related_resource(obj)
            return super(GenericForeignKeyField, self).resource_from_uri(fk_resource, uri, request, related_obj, related_name)
        except ObjectDoesNotExist:
            raise ApiFieldError("Could not find the provided object via resource URI '%s'." % uri)

    def build_related_resource(self, *args, **kwargs):
        self._to_class = None
        return super(GenericForeignKeyField, self).build_related_resource(*args, **kwargs)


# the following is from
# http://gdorn.circuitlocution.com/blog/2012/11/21/using-tastypie-inside-django.html

def rest(path, query={}, data={}, headers={}, method="GET", request=None):
    """
    Converts a RPC-like call to something like a HttpRequest, passes it
    to the right view function (via django's url resolver) and returns
    the result.

    Args:
        path: a uri-like string representing an API endpoint. e.g. /resource/27.
              /api/v2/ is automatically prepended to the path.
        query: dictionary of GET-like query parameters to pass to view
        data: dictionary of POST-like parameters to pass to view
        headers: dictionary of extra headers to pass to view (will end up in request.META)
        method: HTTP verb for the emulated request
    Returns:
        a tuple of (status, content):
            status: integer representing an HTTP response code
            content: string, body of response; may be empty
    """
    #adjust for lack of trailing slash, just in case
    if path[-1] != '/':
        path += '/'

    hreq = FakeHttpRequest()
    hreq.path = '/api/v1' + path
    hreq.GET = query
    if isinstance(data, basestring):
        hreq.POST = data
    else:
        hreq.POST = json.dumps(data)
    hreq.META = headers
    hreq.method = method
    if request:
        hreq.user = request.user
    try:
        view = resolve(hreq.path)
        res = view.func(hreq, *view.args, **view.kwargs)
    except Resolver404:
        return (404, '')

     #container is the untouched content before HttpResponse mangles it
    return (res.status_code, res._container)

class CustomNoneSerializer(Serializer):
    """
    A custom serializer for TastyPie allowing "none" as an encoding type.

    Resources need to specify this serializer as Meta.serializer.
    See http://django-tastypie.readthedocs.org/en/latest/serialization.html

    @todo: Is there a better way to tell TastyPie to not do any serialization per-request
        (without breaking a hypothetical HTTP REST service)?
    """
    formats = Serializer.formats + ['none']
    content_types = Serializer.content_types
    content_types['none'] = 'none/none'

    def to_none(self, data, options=None):
        """
        Outbound 'serializer'.
        """
        #If the object is a tastypie bundle containing a dict, just return the dict.
        if hasattr(data, 'data'):
            return data.data
        elif isinstance(data, dict):
            if 'objects' in data:
                data['objects'] = [foo.data for foo in data['objects']]
        return data

    def from_none(self, data, options=None):
        return data


class FakeHttpRequest(HttpRequest):
    """
    Custom version of Django's HttpRequest to minimize unnecessary work
    for in-process requests.
    """
    _read_started = False

    @property
    def raw_post_data(self):
        """
        Instead of providing a file-like object representing the body
        of the request, just return the internal dict; tastypie copes with
        this just fine.
        """
        return self.POST

    @property
    def encoding(self):
        """
        We're passing python native types around and not encoding anything,
        so all FakeHttpRequests are encoded as 'none/none'.
        """
        return 'none/none'

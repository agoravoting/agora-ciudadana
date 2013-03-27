from functools import wraps
from django.db.models import Model, get_model
from django.db.models.base import ModelBase
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from django.http import Http404

from guardian.exceptions import GuardianError

from tastypie import http
from tastypie.bundle import Bundle
from django.http import HttpRequest
from tastypie.exceptions import ImmediateHttpResponse


def permission_required(perm, lookup_variables=None, **kwargs):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled.

    Optionally, instances for which check should be made may be passed as an
    second argument or as a tuple parameters.

    :param check_static: if set to ``Model``, the permissions will be
    checked in calling to Model.static_has_perms() instead of calling to
    has_perms(). Defaults to ``None``.

    Examples::

    @permission_required('join', (Agora, 'id', 'id'))
    def join(self, request):
    agora = get_object_or_404(Agora, id=id)
    agora.members.append(request.user)
    return self.success()

    @permission_required('create', check_static=Agora)
    def obj_create(self, bundle, request=None, **kwargs):
    user = get_object_or_404(User, username=username)
    return user.get_absolute_url()

    """
    check_static = kwargs.pop('check_static', None)

    if check_static:
        lookup_variables = [check_static]

    # Check if perm is given as string in order not to decorate
    # view function itself which makes debugging harder
    if not isinstance(perm, basestring):
        raise GuardianError("First argument must be in format: "
            "'app_label.codename or a callable which return similar string'")

    def decorator(view_func):
        def wrapped(*args, **kwargs):
            # if more than one parameter is passed to the decorator we try to
            # fetch object for which check would be made
            obj = None
            request = None
            if 'request' in kwargs:
                request = kwargs['request']
            elif 'bundle' in kwargs:
                request = kwargs['bundle'].request
            else:
                for arg in args:
                    if isinstance(arg, HttpRequest):
                        request = arg
                        break
                    elif isinstance(arg, Bundle) and isinstance(arg.request, HttpRequest):
                        request = arg.request
                        break

            if lookup_variables:
                model, lookups = lookup_variables[0], lookup_variables[1:]
                # Parse model
                if isinstance(model, basestring):
                    splitted = model.split('.')
                    if len(splitted) != 2:
                        raise GuardianError("If model should be looked up from "
                            "string it needs format: 'app_label.ModelClass'")
                    model = get_model(*splitted)
                elif issubclass(model.__class__, (Model, ModelBase, QuerySet)):
                    pass
                else:
                    raise GuardianError("First lookup argument must always be "
                        "a model, string pointing at app/model or queryset. "
                        "Given: %s (type: %s)" % (model, type(model)))
                # Parse lookups
                if len(lookups) % 2 != 0:
                    raise GuardianError("Lookup variables must be provided "
                        "as pairs of lookup_string and view_arg")
                lookup_dict = {}
                for lookup, view_arg in zip(lookups[::2], lookups[1::2]):
                    if view_arg not in kwargs:
                        raise GuardianError("Argument %s was not passed "
                            "into view function" % view_arg)
                    lookup_dict[lookup] = kwargs[view_arg]

                if not check_static:
                    try:
                        obj = get_object_or_404(model, **lookup_dict)
                    except Http404:
                        raise ImmediateHttpResponse(response=http.HttpNotFound())

            has_perms = False
            if request:
                if check_static:
                    has_perms = model.static_has_perms(perm, request.user)
                else:
                    has_perms = obj.has_perms(perm, request.user)

            if not has_perms:
                raise ImmediateHttpResponse(response=http.HttpForbidden())

            return view_func(*args, **kwargs)
        return wraps(view_func)(wrapped)
    return decorator
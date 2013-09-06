
from agora_site.agora_core.models import CastVote
from agora_site.misc.utils import rest as rest_api

import json
from urlparse import urlparse, urlunparse
from django.http import QueryDict
from django import template
from django.conf import settings
from django.utils.translation import pgettext as _
from django.template.base import token_kwargs
from django.contrib.contenttypes.models import ContentType

register = template.Library()

@register.filter
def is_content_type(obj, content_type):
    return ContentType.objects.get_for_model(obj).name == content_type

@register.filter
def debug_object(obj, obj2=None):
    import ipdb; ipdb.set_trace()

@register.filter
def is_agora_admin(agora, user):
    return agora.has_perms('admin', user)

@register.filter
def ispair(obj):
    return obj % 2 == 0

@register.filter
def vote_for_election(user, election):
    '''
    Returns the vote of the requested user in the requested election if any
    '''
    try:
        return user.cast_votes.get(is_direct=True, is_counted=True,
            election=election, is_public=True)
    except Exception:
        return None

@register.filter
def get_chained_first_pretty_answer(vote, election):
    try:
        return vote.get_chained_first_pretty_answer(election)
    except:
        # this can happen if for example the vote of the delegate is indeed
        # private
        return None

@register.filter
def last_election_voted(user, agora):
    '''
    Returns the last vote from the user in the given agora if any
    '''
    return user.cast_votes.filter(is_counted=True, election__agora=agora).order_by('-casted_at_date')[0]

@register.filter
def get_perms(obj, user):
    return obj.get_perms(user)

@register.filter
def has_delegated_in_agora(user, agora):
    return user.get_profile().has_delegated_in_agora(agora)

@register.filter
def get_delegation_in_agora(user, agora):
    return user.get_profile().get_delegation_in_agora(agora)

@register.filter
def get_delegate_in_agora(user, agora):
    return user.get_profile().get_delegation_in_agora(agora).get_delegate()

@register.filter
def get_vote_in_election(user, election):
    return user.get_profile().get_vote_in_election(election)

@register.tag
def functioncall():
    """
    Calls to an object's function 

    For example::
        {% functioncall object "function_name" arg1 arg2 %}

        or

        {% functioncall object "function_name" name1=value1 name2=value2  %}

    You can also get the returning value of the function call::
        {% functioncall object "function_name" arg1 arg2 as variable_name %}
    """

    # TODO see django/template/defaulttags.py
    #from django.template.base import token_kwargs
    #def url(parser, token):
    #class URLNode(Node):
    return ''

@register.filter
def getdoublelistitem(item_list, string):
    '''
    Returns an item by key in a double list of type:
    ( (key, value), (key, value), ...)
    '''
    for key, value in item_list:
        if key == string:
            return value
    return ''

@register.filter
def getitem(item, string):
    '''
    Returns an item by key in a dictionary
    '''
    return item.get(string,'')

@register.filter
def getindex(item, index):
    '''
    Returns an item by an index in a list or tuple
    '''
    return item[index]


@register.filter
def list_contains(l, item):
    '''
    Returns if a list contains an item
    '''
    return item in l

@register.filter
def getvote(action):
    return CastVote.objects.get(action_id=action.id)

@register.filter
def pretty_date(date):
    if not date:
        return ''
    return date.strftime(_('Internationalized format for a date, see python '
        'documentation for strftime for more details.', '%B %d'))

@register.filter
def elections_grouped_by_date(elections):
    '''
    Returns the list of elections given, but grouped by relevant dates, in a
    list of pairs like:

        dict(date1=(election1, election2, ...), date2=(election3, election4, ...))
    '''
    grouping = dict()
    last_date = None
    used_elections = []

    for election in elections:
        end_date = None
        if election.voting_extended_until_date:
            end_date = election.voting_extended_until_date.date()

        start_date = None
        if election.voting_starts_at_date:
            start_date = election.voting_starts_at_date.date()

        if not election.has_started() or not end_date:
            if start_date not in grouping:
                grouping[start_date] = (election,)
            elif election not in grouping[start_date]:
                grouping[start_date] += (election,)
        elif not election.has_ended():
            if end_date not in grouping:
                grouping[end_date] = (election,)
            elif election not in grouping[end_date]:
                grouping[end_date] += (election,)

    return grouping

ACTIVE_TAB_NAME = 'ACTIVETABS'
DEFAULT_NAMESPACE = 'default'

class ActiveTabNode(template.Node):

    def __init__(self, name, namespace=None):
        if namespace is None:
            self.namespace = DEFAULT_NAMESPACE
        else:
            self.namespace = namespace
        self.name = name


    def render(self, context):
        if ACTIVE_TAB_NAME not in context:
            context[ACTIVE_TAB_NAME] = dict()

        context[ACTIVE_TAB_NAME][self.namespace] = self.name
        return ''

class IfActiveTabNode(template.Node):
    def __init__(self, nodelist_true, nodelist_false, name, namespace=None):
        if namespace is None:
            self.namespace = DEFAULT_NAMESPACE
        else:
            self.namespace = namespace
        self.name = name

        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false

    def render(self, context):
        if ACTIVE_TAB_NAME not in context\
            or self.namespace not in context[ACTIVE_TAB_NAME]\
            or context[ACTIVE_TAB_NAME][self.namespace] != self.name:
            return self.nodelist_false.render(context)

        return self.nodelist_true.render(context)

class RestNode(template.Node):
    args = None

    def __init__(self, req, method, data, *args):
        self.args = args
        self.method = method
        self.data = data
        self.req = req

    def render(self, context):
        try:
            request = template.Variable(self.req).resolve(context)
            data = ""
            method = "GET"
            if self.method != "GET":
                data = str(template.Variable(self.data).resolve(context))
                method = str(template.Variable(self.method).resolve(context))

            args = [str(template.Variable(arg).resolve(context)) for arg in self.args]
            url = ''.join(args)

            if settings.USE_ESI and method == "GET" and\
                    ('use_esi', False) not in self.args:
                return "<esi:include src=\"/api/v1%s\" />" % url

            # separate query params from url
            (scheme, netloc, path, params, query, fragment) = urlparse(url)
            query_dict = QueryDict(query)
            url = urlunparse((scheme, netloc, path, params, '', fragment))

            status_code, container = rest_api(url, request=request,
                query=query_dict, data=data, method=method)
            if status_code >= 300:
                return ''
            else:
                return container[0]
        except template.VariableDoesNotExist:
            return ''

@register.tag
def rest(parser, token):
    req = token.split_contents()[1]
    method = "GET"
    data = None
    bits = token.split_contents()[2:]
    return RestNode(req, method, data, *bits)


@register.tag
def custom_rest(parser, token):
    req = token.split_contents()[1]
    method = token.split_contents()[2]
    data = token.split_contents()[3]
    bits = token.split_contents()[4:]
    return RestNode(req, method, data, *bits)

@register.tag
def activetab(parser, token):
    bits = token.contents.split()[1:]
    if len(bits) not in (1, 2):
        raise template.TemplateSyntaxError, "Invalid number of arguments"
    if len(bits) == 1:
        namespace = None
        name = bits[0]
    else:
        namespace = bits[0]
        name = bits[1]

    return ActiveTabNode(name, namespace)

@register.tag
def ifactivetab(parser, token):
    bits = token.contents.split()[1:]
    nodelist_true = parser.parse(('else', 'endifactivetab'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endifactivetab',))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()
    if len(bits) not in (1, 2):
        raise template.TemplateSyntaxError, "Invalid number of arguments"
    if len(bits) == 1:
        namespace = None
        name = bits[0]
    else:
        namespace = bits[0]
        name = bits[1]
    return IfActiveTabNode(nodelist_true, nodelist_false, name, namespace)

@register.tag
def raw(parser, token):
    # Whatever is between {% raw %} and {% endraw %} will be preserved as
    # raw, unrendered template code.
    text = []
    parse_until = 'endraw'
    tag_mapping = {
        template.TOKEN_TEXT: ('', ''),
        template.TOKEN_VAR: ('{{', '}}'),
        template.TOKEN_BLOCK: ('{%', '%}'),
        template.TOKEN_COMMENT: ('{#', '#}'),
    }
    # By the time this template tag is called, the template system has already
    # lexed the template into tokens. Here, we loop over the tokens until
    # {% endraw %} and parse them to TextNodes. We have to add the start and
    # end bits (e.g. "{{" for variables) because those have already been
    # stripped off in a previous part of the template-parsing process.
    while parser.tokens:
        token = parser.next_token()
        if token.token_type == template.TOKEN_BLOCK and token.contents == parse_until:
            return template.TextNode(u''.join(text))
        start, end = tag_mapping[token.token_type]
        text.append(u'%s%s%s' % (start, token.contents, end))
    parser.unclosed_block_tag(parse_until)

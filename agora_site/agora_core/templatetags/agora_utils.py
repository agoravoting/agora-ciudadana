
from agora_site.agora_core.models import CastVote

from django import template
from django.utils.translation import pgettext as _
from django.template.base import token_kwargs
register = template.Library()

@register.filter
def debug_object(obj, obj2=None):
    import ipdb; ipdb.set_trace()

@register.filter
def vote_for_election(user, election):
    '''
    Returns the vote of the requested user in the requested election if any
    '''
    return user.cast_votes.get(is_direct=True, is_counted=True,
        election=election, is_public=True)

@register.filter
def last_election_voted(user, agora):
    '''
    Returns the last vote from the user in the given agora if any
    '''
    return user.cast_votes.filter(is_counted=True, election__agora=agora).order_by('-casted_at_date')[0]

@register.filter
def get_perms(election, user):
    return election.get_perms(user)

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
def getvote(action):
    return CastVote.objects.get(action_id=action.id)

@register.filter
def pretty_date(date):
    return date.strftime(_('Internationalized format for a date, see python '
        'documentation for strftime for more details.', '%B %d'))

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

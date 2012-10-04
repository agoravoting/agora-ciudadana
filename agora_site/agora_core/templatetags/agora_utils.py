
from agora_site.agora_core.models import CastVote

from django import template
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
    return vote.get_chained_first_pretty_answer(election)

@register.filter
def last_election_voted(user, agora):
    '''
    Returns the last vote from the user in the given agora if any
    '''
    return user.cast_votes.filter(is_counted=True, election__agora=agora).order_by('-casted_at_date')[0]

@register.filter
def get_perms(election, user):
    return election.get_perms(user)

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
def getvote(action):
    return CastVote.objects.get(action_id=action.id)

@register.filter
def pretty_date(date):
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

    for election in elections:
        end_date = None
        if election.voting_extended_until_date:
            end_date = election.voting_extended_until_date.date()

        start_date = election.voting_starts_at_date.date()

        if start_date not in grouping:
            grouping[start_date] = (election,)
        elif election not in grouping[start_date]:
            grouping[start_date] += (election,)

        if end_date and start_date != end_date:
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

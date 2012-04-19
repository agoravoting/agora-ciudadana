from django import template
from django.utils.translation import pgettext as _

register = template.Library()

@register.filter
def getitem(item, string):
    '''
    Returns an item by key in a dictionary
    '''
    return item.get(string,'')

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

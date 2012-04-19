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
import re
from django import template

register = template.Library()

@register.filter
def truncate_words(string, num_max_words=1):
        return ' '.join(string.split(' ')[:num_max_words])


urlfinder = re.compile('^(http:\/\/\S+)')
urlfinder2 = re.compile('\s(http:\/\/\S+)')
@register.filter('urlify_markdown')
def urlify_markdown(value):
    value = urlfinder.sub(r'<\1>', value)
    return urlfinder2.sub(r' <\1>', value)

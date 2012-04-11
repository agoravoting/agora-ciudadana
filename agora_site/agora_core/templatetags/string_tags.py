from django import template

register = template.Library()

@register.filter
def truncate_words(string, num_max_words=1):
        return ' '.join(string.split(' ')[:num_max_words])

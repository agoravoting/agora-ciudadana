from django.utils import simplejson as json
from django.utils.text import force_unicode

from actstream.models import Action


def dateify(datetime):
    return datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')

class Serializer(object):
    def id(self, object):
        return force_unicode(object.pk)

    def url(self, object):
        if hasattr(object, 'get_absolute_url') and callable(object.get_absolute_url):
            return object.get_absolute_url()

    def object_type(self, object):
        return '%s.%s' % (object._meta.app_label, object._meta.module_name)

    def published(self, action):
        return dateify(action.timestamp)

    def title(self, action):
        return force_unicode(action)

    def verb(self, action):
        return action.verb

    def action_attrs(self, action):
        return  {
            'published': self.published(action),
            'title': self.title(action),
            'verb': self.verb(action),
            'actor': self.actor(action)
        }

    def object_formatter(func):
        def inner(self, action):
            object = getattr(action, func.__name__)
            return {
                'url': self.url(object),
                'id': self.id(object),
                'objectType': self.object_type(object),
                'displayName': force_unicode(object),
            }
        return inner

    @object_formatter
    def actor(self):
        pass

    @object_formatter
    def target(self):
        pass

    @object_formatter
    def action_object(self):
        pass

    def prepare(self, action_or_queryset):
        data = []
        if isinstance(action_or_queryset, Action):
            actions = [action_or_queryset]
        else:
            actions = action_or_queryset
        for action in actions:
            action_data = self.action_attrs(action)
            if action.action_object:
                action_data['object'] = self.action_object(action)
            if action.target:
                action_data['target'] = self.target(action)
            data.append(action_data)
        return data

    def serialize(self, action_or_queryset, **kwargs):
        data = {'items': self.prepare(action_or_queryset)}
        if 'fp' in kwargs:
            return json.dump(data, kwargs.pop('fp'), **kwargs)
        return json.dumps(data, **kwargs)

class XMLSerializer(ActivityStreamSerializer):
    def serialize(self, action_or_queryset, **kwargs):
        

from pprint import pprint
pprint(json.loads(ActivityStreamSerializer().serialize(Action.objects.all())))
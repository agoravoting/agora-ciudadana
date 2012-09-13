from django.utils import simplejson
from dajaxice.decorators import dajaxice_register

from agora_site.agora_core.models import Agora

from django.utils.simplejson import dumps, loads, JSONEncoder
from django.core.urlresolvers import reverse
from django.db.models.query import QuerySet
from agora_site.agora_core.models import Election
from agora_site.agora_core.templatetags.agora_utils import *
import datetime

def toDict(obj):
    """
        Pre-processor to prepare objects that simplejson cannot serialize
    """
    
    if isinstance(obj, QuerySet):
        return [toDict(i) for i in obj]
    elif isinstance(obj, tuple):
        return [toDict(i) for i in obj]
    elif isinstance(obj, list):
        return [toDict(i) for i in obj]
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return dict((toDict(k), toDict(v)) for (k,v) in obj.items())
    elif isinstance(obj, Agora):
        url = reverse('agora-view', None, [str(obj.creator.username), str(obj.name)])
        return {'username': obj.creator.username,'name': obj.name, 'url': url}
    elif isinstance(obj, Election):
        url = reverse('election-view', None, [str(obj.agora.creator.username), str(obj.agora.name), str(obj.name)])
        
        return {'username': obj.creator.username,'name': obj.name, 'url': url, 'pretty_name': obj.pretty_name}
    else:
        return obj

@dajaxice_register
def searchAgoras(request, userid, search):
    """
        Ajax endpoint, used from user-view
    """
    if(len(search) > 0):
        agoras = Agora.objects.filter(name__startswith=search, creator__id=userid)
    else:
        agoras = Agora.objects.all()
        
    if(len(agoras) > 0):
        return dumps({'error': 0, 'data': toDict(agoras)})
    else:
        return dumps({'error': 0, 'data': []})
        
@dajaxice_register
def searchElections(request, agoraid, search):
    """
        Ajax endpoint, used from agora-view
    """
    agoras = Agora.objects.filter(id=agoraid)
    if(len(agoras) == 1):
        agora = agoras[0]
        
        if(len(search) > 0):
            tmp = agora.get_open_elections_with_name_start(search)
        else:
            tmp = agora.get_open_elections()

        elections = [{'date': k, 'pretty_date': pretty_date(k), 'elections': v} for (k,v) in elections_grouped_by_date(tmp).items()]
        
        if(len(elections) > 0):
            return dumps({'error': 0, 'data': toDict(elections)})
        else:
            return dumps({'error': 0, 'data': []})
    else:
        return dumps({'error': 1, 'message': 'Agora ' + `agoraid` + ' not found'})
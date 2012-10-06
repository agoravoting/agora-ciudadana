from django.utils import simplejson
from django.template.defaultfilters import *

from dajaxice.decorators import dajaxice_register

from agora_site.agora_core.models import Agora, CastVote
from django.contrib.auth.models import User

from django.shortcuts import get_object_or_404
from django.utils.simplejson import dumps, loads, JSONEncoder
from django.core.urlresolvers import reverse
from django.db.models.query import QuerySet
from agora_site.agora_core.models import Election
from agora_site.agora_core.templatetags.agora_utils import *
import datetime

def preJson(obj):
    """
        Pre-processor to prepare objects that simplejson cannot serialize
    """

    if isinstance(obj, QuerySet) or isinstance(obj, tuple) or isinstance(obj, list):
        return [preJson(i) for i in obj]
    elif isinstance(obj, datetime.date) or isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return dict((preJson(k), preJson(v)) for (k,v) in obj.items())
    elif isinstance(obj, Agora):
        url = reverse('agora-view', None, [str(obj.creator.username), str(obj.name)])
        return {'username': obj.creator.username,'name': obj.name, 'url': url}
    elif isinstance(obj, Election):
        url = reverse('election-view', None, [str(obj.agora.creator.username), str(obj.agora.name), str(obj.name)])

        ret = {'username': obj.creator.username,'name': obj.name, 'url': url, 'pretty_name': obj.pretty_name}
        if(obj.result_tallied_at_date != None):
            ret.update({
                'tallied_date_pretty': pretty_date(obj.result_tallied_at_date),
                'tallied_date': preJson(obj.result_tallied_at_date),
                'winner': getitem(obj.get_winning_option(), 'value'),
                'votes': getitem(obj.get_winning_option(), 'total_count'),
                'bar_width': floatformat(getitem(obj.get_winning_option(), 'total_count_percentage'))
            })

        return ret
    else:
        return obj

@dajaxice_register
def searchAgoras(request, userid, search):
    """
        Ajax endpoint, used from user-view and home-loggedin-activity
    """
    search = search.strip()
    if userid:
        user = get_object_or_404(User, pk=userid)
        agoras = user.agoras
    else:
        agoras = Agora.objects

    if(len(search) > 0):
        agoras = agoras.filter(name__icontains=search, creator__id=userid).order_by('name')

    if(agoras.count() > 0):
        return dumps({'error': 0, 'data': preJson(agoras.all())})
    else:
        return dumps({'error': 0, 'data': []})

@dajaxice_register
def searchElectionsForUserPage(request, userid, search):
    """
    Ajax endpoint, used from home-loggedin-activity
    """
    search = search.strip()
    users = User.objects.filter(id=userid)
    if(len(users) == 1):
        user = users[0]

        ret = []
        for election in user.get_profile().get_participated_elections().filter(pretty_name__icontains=search).all()[0:5]:
            vote = user.get_profile().get_vote_in_election(election)
            if vote and vote.is_public:
                pretty_answer = vote.get_chained_first_pretty_answer(election)
                ret +=  [{'election': election, 'is_public': vote.is_public, 'pretty_answer': pretty_answer, 'shown_user': user.username}]
            else:
                ret +=  [{'election': election, 'is_public': vote.is_public, 'shown_user': user.username}]

        return dumps({'error': 0, 'data': preJson(ret)})
    else:
        return dumps({'error': 1, 'message': 'User ' + `userid` + ' not found'})

@dajaxice_register
def searchElectionsForUser(request, userid, search):
    """
        Ajax endpoint, used from user-view
    """
    search = search.strip()
    user = get_object_or_404(User, pk=userid)
    tmp = user.get_profile().get_open_elections(search)

    elections = [{
        'date': k,
        'pretty_date': pretty_date(k),
        'elections': [{
            'url': election.url,
            'pretty_name': election.pretty_name,
            'has_user_voted': election.has_user_voted(user),
            'has_user_voted_via_a_delegate': election.has_user_voted_via_a_delegate(user)
        } for election in v]
    } for (k,v) in elections_grouped_by_date(tmp).items()]

    if(len(elections) > 0):
        return dumps({'error': 0, 'data': preJson(elections)})
    else:
        return dumps({'error': 0, 'data': []})

@dajaxice_register
def searchElectionsForAgora(request, agoraid, search):
    """
        Ajax endpoint, used from agora-view
    """
    search = search.strip()
    agoras = Agora.objects.filter(id=agoraid)

    if(len(agoras) == 1):
        agora = agoras[0]

        if(len(search) > 0):
            tmp = agora.get_open_elections_with_name_start(search)
        else:
            tmp = agora.get_open_elections()

        elections = [{
            'date': k,
            'pretty_date': pretty_date(k),
            'elections': [{
                'url': election.url,
                'pretty_name': election.pretty_name,
                'has_user_voted': election.has_user_voted(request.user),
                'has_user_voted_via_a_delegate': election.has_user_voted_via_a_delegate(request.user)
            } for election in v]
        } for (k,v) in elections_grouped_by_date(tmp).items()]

        if(len(elections) > 0):
            return dumps({'error': 0, 'data': preJson(elections)})
        else:
            return dumps({'error': 0, 'data': []})
    else:
        return dumps({'error': 1, 'message': 'Agora ' + `agoraid` + ' not found'})
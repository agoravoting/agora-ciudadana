import string
import random
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

from agora_site.agora_core.models import User
from agora_site.agora_core.models import Agora
from agora_site.agora_core.models import Election


def create_user(username, email, agora=None):
    pwd = ''.join([random.choice(string.letters+string.digits) for _ in range(8)])

    u = User(username=username, email=email)
    u.set_password(pwd)
    u.first_name = username
    u.is_active = True
    u.save()

    if agora:
        u.get_profile().add_to_agora(agora_name=agora)

    return u


def create_agora(agoraname, pretty, img=None, creator=None):
    if not creator:
        creator = User.objects.filter(is_superuser=True)[0]

    a = Agora(creator=creator, name=agoraname, pretty_name=pretty, image_url=img)
    a.membership_policy = "JOINING_REQUIRES_ADMINS_APPROVAL"
    a.comments_policy = "NO_COMMENTS"
    a.delegation_policy = "DISALLOW_DELEGATION"

    domain = Site.objects.get(pk=1).domain
    a.url = "http://" + domain + reverse('agora-view', kwargs=dict(username=creator.username, agoraname=a.name))

    a.save()

    a.members.add(creator)
    a.admins.add(creator)


def add_census(agoraname, censusfile):
    a = Agora.objects.get(name=agoraname)

    with open(censusfile) as f:
        for line in f.readlines():
            e = line.strip().lower()
            if not e:
                continue

            try:
                u = User.objects.get(email=e)
            except:
                username = 'voter%04d' % User.objects.count()
                u = create_user(username, e)

            # TODO Change password and send an email for this election
            a.members.add(u)


def remove_census(agoraname):
    a = Agora.objects.get(name=agoraname)
    a.members.clear()
    a.admins.clear()
    a.members.add(a.creator)
    a.admins.add(a.creator)


COMMANDS = {
    'create_user': ('<username> <email> [agora]', create_user),
    'create_agora': ('<agoraname> <prettyname> [imgurl] [creator]', create_agora),
    'add_census': ('<agoraname> <census file>', add_census),
    'remove_census': ('<agoraname>', remove_census),
}

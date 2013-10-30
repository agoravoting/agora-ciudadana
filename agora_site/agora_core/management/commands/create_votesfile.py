# Copyright (C) 2013 Eduardo Robles Elvira <edulix AT wadobo DOT com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from agora_site.agora_core.models import (Agora, Election, Profile, CastVote,
                                          Authority)
from agora_site.misc.utils import *
from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora
from agora_site.agora_core.models.voting_systems.base import (
    parse_voting_methods, get_voting_system_by_id)

from actstream.signals import action

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.utils import translation, timezone
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.crypto import constant_time_compare
from django.core.management.base import BaseCommand, CommandError

from celery.contrib import rdb
from celery import task

import datetime
import codecs
import requests
import tarfile
import uuid
import json
import os
import shutil
from random import choice
import random

class Command(BaseCommand):
    '''
    Creates the votes file for an encrypted file
    '''

    args = '<n>'
    help = 'Adds n test users'

    def handle(self, *args, **options):
        try:
            n = int(args[0])
        except:
            raise CommandError("You need to provide a valid election id")

        # stores delegation status data in the following format:
        # {
        #     'election_id: "",
        #     'create_status: 'success',
        #     'create_director_id': <id>,
        #     'tally_status: 'success|requested|error requesting|error',
        #     'tally_director_id': <id>,
        # }
        orchestra_status = JSONField(null=True)
        election = Election.objects.get(pk=n)
        auths = election.authorities.all()
        director = choice(auths)

        # create votes file and do hash. Note: currently we do not count delegated
        # votes
        votes_path = os.path.join(settings.MEDIA_ROOT, 'elections', str(election.id),
            election.orchestra_status['election_id'], 'votes')

        if os.path.exists(os.path.dirname(votes_path)):
            shutil.rmtree(os.path.dirname(votes_path))

        os.makedirs(os.path.dirname(votes_path))

        with codecs.open(votes_path, encoding='utf-8', mode='w') as votes_file:
            for vote in election.get_direct_votes():
                proofs = []
                choices = []
                i = 0
                for question in election.questions:
                    q_answer = vote.data['answers'][i]

                    proofs.append(dict(
                        commitment=q_answer['commitment'],
                        response=q_answer['response'],
                        challenge=q_answer['challenge']
                    ))
                    choices.append(dict(
                        alpha=q_answer['alpha'],
                        beta=q_answer['beta']
                    ))
                    i += 1
                vote_json = dict(
                    proofs=proofs,
                    choices=choices
                )
                votes_file.write(json.dumps(vote_json) + "\n")

        proto = "https://" if settings.AGORA_USE_HTTPS else "http://"
        votes_url = proto + Site.objects.all()[0].domain + "/media/elections/%d/%s/votes" % (
            election.id, election.orchestra_status['election_id'])
        votes_hash = hash_file(votes_path)

        tally_data = {
            "election_id": election.orchestra_status['election_id'],
            "callback_url": "https://127.0.0.1:5000/public_api/receive_tally",
            "extra": [],
            "votes_url": votes_url,
            "votes_hash":"sha512://" + votes_hash
        }
        print json.dumps(tally_data)

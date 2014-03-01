# Copyright (C) 2014 Eduardo Robles Elvira <edulix AT wadobo DOT com>
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

from django.core.management.base import BaseCommand, CommandError
from agora_site.agora_core.models import *
from django.contrib.auth.models import User

import json


class Command(BaseCommand):
    args = ''
    help = 'Imports from first arg file users to current installation'

    def handle(self, *args, **options):
        with open(args[0], 'r') as f:
            user_list = json.loads(f.read())

        for data in user_list:
            if User.objects.filter(username=data['username']).exists() or\
                    User.objects.filter(email=data['email']).exists():
                print("user %s already exists.." % data["username"])
                if User.objects.filter(username=data['username']).exists():
                    u = User.objects.get(username=data['username'])
                else:
                    u = User.objects.get(email=data['email'])
            else:
                u = User(username=data['username'], email=data['email'])
                u.password= data['password']
                u.first_name = data['first_name']
                u.is_active = True
                u.save()

            # add user to the default agoras if any
            for agora_name in data["agoras"]:
                u.get_profile().add_to_agora(agora_name=agora_name, silent=False)

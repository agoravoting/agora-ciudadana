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
    help = 'Exports to stdout the users in the current installation'

    def handle(self, *args, **options):
        l = []
        for u in User.objects.filter(is_active=True):
            l.append(dict(
                username=u.username,
                email=u.email,
                password=u.password,
                first_name=u.first_name,
                agoras=[a.get_full_name() for a in u.agoras.all()]
            ))
        print(json.dumps(l, indent=4))
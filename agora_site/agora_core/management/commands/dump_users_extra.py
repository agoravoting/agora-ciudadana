# Copyright (C) 2014 Eduardo Robles Elvira <edulix AT agoravoting DOT com>
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
from django.conf import settings

class Command(BaseCommand):
    args = ''
    help = 'Exports to stdout the users extra data in the current installation in CSV format'

    def handle(self, *args, **options):

        for u in User.objects.filter(is_active=True):
            extra = u.get_profile().extra
            if not isinstance(extra, dict):
                continue

            l = [extra.get(el['field_name'], '') for el in settings.AGORA_REGISTER_EXTRA_FIELDS]
            if reduce(lambda a, b: len(a) + len(b), l) > 0:
                print(",".join(l))

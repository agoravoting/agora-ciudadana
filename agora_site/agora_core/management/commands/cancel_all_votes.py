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
from django.utils import timezone

from agora_site.agora_core.models.election import Election

class Command(BaseCommand):
    args = ''
    help = 'Cancels all votes of the specified election'

    def handle(self, *args, **options):
        try:
            name = args[0]
        except:
            raise CommandError("usage: <election.name>")

        e = Election.objects.get(name=name)
        for vote in e.get_direct_votes():
            vote.invalidated_at_date = timezone.now()
            vote.is_counted = False
            vote.save()

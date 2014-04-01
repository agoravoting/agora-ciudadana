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


from django.core.management.base import BaseCommand, CommandError
from agora_site.agora_core.models.election import Election
from agora_site.agora_core.tasks.election import receive_tally

class Command(BaseCommand):
    '''
    Uses a tally.tar.gz file to set the results of an election
    '''

    args = '<n>'
    help = 'Process manually an election tally and set the results'

    def handle(self, *args, **options):
        try:
            election_name = args[0]
            tally_path = args[1]
        except:
            raise CommandError("usage: <election_name> <tally_path>")

        if not os.path.exists(tally_path):
            raise CommandError("tally path doesn't exist")

        e = Election.objects.get(name=election_name)
        receive_tally(e.id, None, True, 0, True, tally_path)

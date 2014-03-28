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
from agora_site.agora_core.models.election import Election
from agora_site.agora_core.tasks.election import launch_encrypted_tally

class Command(BaseCommand):
    '''
    A partial tally launches the tally in election-orchestra authorities, and
    it can be safely launched in the middle of an election without having to
    close it. The results remain in the election authorities and are not
    sent back to agora.

    NOTE: after doing a partial tally, you'll have to execute reset-tally <eid>
    in each election authority to be able to do any partial or normal tally of
    the same election.
    '''
    args = ''
    help = 'Computes a partial tally of an election'

    def handle(self, *args, **options):
        try:
            name = args[0]
        except:
            raise CommandError("usage: <election.name>")

        e = Election.objects.get(name=name)
        launch_encrypted_tally(e, partial=True)

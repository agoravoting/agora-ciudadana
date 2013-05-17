# Copyright (C) 2012 Eduardo Robles Elvira <edulix AT wadobo DOT com>
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
from agora_site.agora_core.models.delegateelectioncount import DelegateElectionCount

import random


class Command(BaseCommand):
    args = ''
    help = 'Recalculates election results'


    def update_election(self, e):
        date = e.result_tallied_at_date
        e.compute_result()
        e.result_tallied_at_date = date
        e.save()

        for dec in DelegateElectionCount.objects.filter(election=e):
            dec.created_at_date = date
            dec.save()

    def handle(self, *args, **options):
        elections = Election.objects.filter(result_tallied_at_date__isnull=False)

        for election in elections:
            self.update_election(election)

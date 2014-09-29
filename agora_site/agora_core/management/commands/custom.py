# Copyright (C) 2012 Daniel Garcia Moreno <danigm AT wadobo DOT com>
# Copyright (C) 2012, 2013 Eduardo Robles Elvira <edulix AT wadobo DOT com>
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

from agora_site import custom
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
import random


class Command(BaseCommand):
    args = '<command> [command args]'
    help = 'Run the custom management command:\n\t' + '\n\t'.join(c + " " +" " + v[0] for c, v in custom.COMMANDS.items())

    def handle(self, *args, **options):
        if not len(args):
            raise CommandError("You need to provide a management command")

        command = args[0]
        cargs = args[1:]
        if not command in custom.COMMANDS:
            raise CommandError("Invalid command")

        custom.COMMANDS[command][1](*cargs)

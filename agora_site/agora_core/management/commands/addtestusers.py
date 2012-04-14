# Copyright (C) 2012 Daniel Garcia Moreno <danigm AT wadobo DOT com>
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
from django.contrib.auth.models import User

import random


names = ['Juan', 'Antonio', 'Jose', 'Carmen', 'Isabel', 'Daniel',
         'David', 'Moises', 'Monica', 'Juana', 'Maria', 'Victoria']
surnames = ['Garcia', 'Bonilla', 'Lopez', 'Perez', 'Ariza', 'Aguilar',
            'Moreno', 'Robles', 'Cuesta', 'Molero', 'Romero']
locations = ['Cordoba', 'Sevilla', 'Huelva', 'Cadiz', 'Malaga',
             'Granada', 'Almeria', 'Jaen']
desc = 'Vivamus fermentum semper porta. Nunc diam velit, adipiscing ut tristique vitae, sagittis vel odio. Maecenas convallis ullamcorper ultricies. Curabitur ornare, ligula semper consectetur sagittis, nisi diam iaculis velit, id fringilla sem nunc vel mi. Nam dictum, odio nec pretium volutpat, arcu ante placerat erat, non tristique elit urna et turpis. Quisque mi metus, ornare sit amet fermentum et, tincidunt et orci. Fusce eget orci a orci congue vestibulum. Ut dolor diam, elementum et vestibulum eu, porttitor vel elit. Curabitur venenatis pulvinar tellus gravida ornare. Sed et erat faucibus nunc euismod ultricies ut id justo. Nullam cursus suscipit nisi, et ultrices justo sodales nec. Fusce venenatis facilisis lectus ac semper. Aliquam at massa ipsum. Quisque bibendum purus convallis nulla ultrices ultricies. Nullam aliquam, mi eu aliquam tincidunt, purus velit laoreet tortor, viverra pretium nisi quam vitae mi. Fusce vel volutpat elit. Nam sagittis nisi dui.'.split(' ')

class Command(BaseCommand):
    args = '<n>'
    help = 'Adds n test users'

    def handle(self, *args, **options):
        try:
            n = int(args[0])
        except:
            raise CommandError("You need to provide the number of users to add")


        for i in range(n):
            uid = i + 1
            u = User(username='user%s' % uid, email='user%s@agoraciudadana.com' % uid, )
            u.set_password('123')
            u.first_name = "%s %s" % (random.choice(names), random.choice(surnames))
            u.is_active = True
            u.save()

            p = u.get_profile()
            p.short_description = ' '.join(random.choice(desc) for i in range(15))
            p.biography = ' '.join(random.choice(desc) for i in range(100))
            p.save()
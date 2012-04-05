# Copyright (C) 2010 Eduardo Robles Elvira <edulix AT wadobo DOT com>
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

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin
from agora_site.agora_core.models import Profile, Agora, Election, CastVote
from reversion.admin import VersionAdmin

admin.site.unregister(User)

class ProfileInline(admin.StackedInline):
    model = Profile

class ProfileAdmin(VersionAdmin):
    inlines = [ProfileInline]
    model = User
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_active', 'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Groups'), {'fields': ('groups',)}),
    )

admin.site.register(User, ProfileAdmin)

admin.site.register(Agora, VersionAdmin)

admin.site.register(Election, VersionAdmin)

admin.site.register(CastVote, VersionAdmin)

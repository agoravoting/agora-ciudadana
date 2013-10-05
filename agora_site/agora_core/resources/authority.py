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

from tastypie import fields

from agora_site.misc.generic_resource import GenericResource, GenericMeta
from agora_site.agora_core.models import Authority

class AuthorityResource(GenericResource):
    class Meta(GenericMeta):
        queryset = Authority.objects.select_related('agora')\
            .filter(is_active=True)
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        excludes = ['url']

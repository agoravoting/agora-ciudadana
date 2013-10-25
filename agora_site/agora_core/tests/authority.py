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

from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase


class AuthorityTest(RootTestCase):
    def test_list_available_authorities(self):
        data = self.getAndParse('authority/')
        auths = data['objects']

        self.assertEqual(len(auths), 3)
        self.assertEqual(set(auths[0].keys()),
            set(['public_url', 'ssl_certificate', 'description', 'name', 'id',
                 'is_active'])
        )

    def test_agora_authorities(self):
        # get available authorities
        data = self.getAndParse('authority/')
        auths = data['objects']

        # get current agora authorities, should be none
        data = self.getAndParse('agora/1/authorities/')
        self.assertEqual(len(data['objects']), 0)

        orig_data = {
            'action': 'set_authorities',
            'authorities_ids': [auths[0]['id'], auths[1]['id']]
        }
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        self.login('david', 'david')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # get current agora authorities, should be 2
        data = self.getAndParse('agora/1/authorities/')
        self.assertEqual(len(data['objects']), 2)
        self.assertEqual(data['objects'][0]['id'], auths[0]['id'])
        self.assertEqual(data['objects'][1]['id'], auths[1]['id'])

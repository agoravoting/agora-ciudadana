from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase


class ElectionTest(RootTestCase):
    def test_election(self):
        # all
        data = self.getAndParse('election/')
        elections = data['objects']
        self.assertEqual(len(elections), 3)

    def test_election_find(self):
        # find
        data = self.getAndParse('election/3/')
        self.assertEquals(data['name'], 'electionone')

        data = self.getAndParse('election/4/')
        self.assertEquals(data['name'], 'electiontwo')

        data = self.get('election/200/', code=HTTP_NOT_FOUND)

    def test_election_permissions(self):
        orig_data = {
            'action': 'get_permissions',
        }

        # anonymous has no permissions
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data["permissions"], [])

        # user1 is not a member but has some permissions
        self.login('user1', '123')
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(set(data["permissions"]),
            set(['join', 'comment', 'create_election']))

        # david is an admin
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(set(data["permissions"]),
            set(['admin', 'delete', 'comment', 'create_election']))
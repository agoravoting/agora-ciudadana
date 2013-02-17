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

    def test_approve_election(self):
        self.login('user1', '123')
        # user1 creates an election, but remains in requested status as it's not
        # an admin
        orig_data = {
            'action': "create_election",
            'pretty_name': "foo bar",
            'description': "foo bar foo bar",
            'question': "Do you prefer foo or bar?",
            'answers': ["fo\"o", "bar"],
            'is_vote_secret': True,
            'from_date': '',
            'to_date': '',
        }
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        self.assertTrue('is_approved' in data)
        self.assertEquals(data['is_approved'], False)
        election_id = data['id']

        # check the election is there
        data2 = self.getAndParse('election/%s/' % election_id, code=HTTP_OK)
        self.assertEqual(data['pretty_name'], data2['pretty_name'])

        # election is in requested elections list
        data = self.getAndParse('agora/1/requested_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(data['objects'][0]['id'], election_id)

        # try to approve election with user1 - prohibited, it has no admin perms
        orig_data = dict(action='approve')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # election is still in requested_elections
        data = self.getAndParse('agora/1/requested_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)

        # approve election
        self.login('david', 'david')
        orig_data = dict(action='approve')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # check that the election is approved
        data = self.getAndParse('election/%s/' % election_id, code=HTTP_OK)
        self.assertTrue('is_approved' in data)
        self.assertEquals(data['is_approved'], True)

        # check that election is not in requested elections
        data = self.getAndParse('agora/1/requested_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 0)
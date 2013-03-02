from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase
from datetime import datetime, timedelta


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


    def test_change_election(self):
        self.login('user1', '123')
        # user1 creates an election, but remains in requested status
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
        election_id = data['id']
        self.assertEquals(data['pretty_name'], orig_data['pretty_name'])

        # change pretty_name
        orig_data = {
            'pretty_name': "fooooooooooooooo bar"
        }
        data = self.putAndParse('election/%d/' % election_id, data=orig_data,
            content_type='application/json')
        self.assertEquals(data['pretty_name'], orig_data['pretty_name'])

        # change answers
        orig_data = {
            'answers': ["uno", "dos", "o tres"]
        }
        data = self.putAndParse('election/%d/' % election_id, data=orig_data,
            content_type='application/json')

        # change answers with one answer > fail
        orig_data = {
            'answers': ["uno"]
        }
        data = self.putAndParse('election/%d/' % election_id, data=orig_data,
            code=HTTP_BAD_REQUEST, content_type='application/json')

        # set start date
        orig_data = {
            'from_date': '2020-02-18 20:13:00'
        }
        data = self.putAndParse('election/%d/' % election_id, data=orig_data,
            content_type='application/json')
        self.assertEquals(orig_data['from_date'], str(datetime.strptime(data['voting_starts_at_date'], "%Y-%m-%dT%H:%M:%S")))

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

    def test_approve_election2(self):
        self.login('user1', '123')
        # user1 creates an election, but remains in requested status as it's not
        # an admin
        date_format = "%Y-%m-%dT%H:%M:%S"
        now = (datetime.now() + timedelta(seconds=1)).strftime(date_format)
        later = (datetime.now() + timedelta(hours=2)).strftime(date_format)
        orig_data = {
            'action': "create_election",
            'pretty_name': "foo bar",
            'description': "foo bar foo bar",
            'question': "Do you prefer foo or bar?",
            'answers': ["fo\"o", "bar"],
            'is_vote_secret': True,
            'from_date': now,
            'to_date': later,
        }
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        self.assertTrue('is_approved' in data)
        self.assertEquals(data['is_approved'], False)
        election_id = data['id']
        election_start_date = data['voting_starts_at_date']

        # election can be approved
        self.login('david', 'david')
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('approve_election' in data["permissions"])

        # sleep for a second
        from time import sleep
        sleep(2)

        # election can still be approved
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('approve_election' in data["permissions"])

        # because start date has been reset
        data = self.getAndParse('election/%s/' % election_id, code=HTTP_OK)
        self.assertEqual(data['voting_starts_at_date'], None)
        self.assertEqual(data['voting_ends_at_date'], None)

    def test_start_election(self):
        # create election as admin
        self.login('david', 'david')
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
        self.assertEquals(data['is_approved'], True)
        election_id = data['id']

        # user1 tries to start election - no permissions
        self.login('user1', '123')
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # user1 didn't have perms, that's why
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('begin_election' not in data["permissions"])

        # and election is not yet in open elections
        data = self.getAndParse('agora/1/open_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 0)

        # david has perms to start the election
        self.login('david', 'david')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('begin_election' in data["permissions"])

        # so he starts the election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # now the election is listed as an open election
        data = self.getAndParse('agora/1/open_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(data['objects'][0]['id'], election_id)

        # and it has a start date
        data = self.getAndParse('election/%s/' % election_id,  code=HTTP_OK)
        self.assertTrue(data['voting_starts_at_date'] is not None)

        # and it cannot be restarted
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # because it has no perms to do it - it already started!
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('begin_election' not in data["permissions"])
        self.assertTrue('end_election' in data["permissions"])
        self.assertTrue('emit_direct_vote' in data["permissions"])


    def test_stop_election(self):
        # create election as admin
        self.login('david', 'david')
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
        election_id = data['id']

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user1 tries to end and tally the election - no permissions
        self.login('user1', '123')
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # user1 didn't have perms, that's why
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('end_election' not in data["permissions"])

        # david has perms to end the election
        self.login('david', 'david')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('end_election' in data["permissions"])

        # so he ends the election
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # now the election is listed as a tallied election
        data = self.getAndParse('agora/1/tallied_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(data['objects'][0]['id'], election_id)

        # and it has an end date
        data = self.getAndParse('election/%s/' % election_id,  code=HTTP_OK)
        self.assertTrue(data['voting_ends_at_date'] is not None)

        # and it cannot be ended again
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # because it has no perms to do it - it already finished!
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('begin_election' not in data["permissions"])
        self.assertTrue('end_election' not in data["permissions"])
        self.assertTrue('emit_direct_vote' not in data["permissions"])


    def test_archive_election(self):
        # create election as admin
        self.login('david', 'david')
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
        election_id = data['id']

        # check it can archive the election
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('archive_election' in data["permissions"])

        # archive the election
        orig_data = dict(action='archive')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # check it cannot archive the election anymore
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('archive_election' not in data["permissions"])

        # because start date has been reset
        data = self.getAndParse('election/%s/' % election_id, code=HTTP_OK)
        self.assertEqual(data['voting_starts_at_date'], None)

    def test_vote_on_election(self):
        # create election as admin
        self.login('david', 'david')
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
        election_id = data['id']

        # david tries to vote but can't, because voting has not started
        vote_data = {
            'is_vote_secret': True,
            'question0': "fo\"o",
            'action': 'vote'
        }
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_FORBIDDEN, content_type='application/json')

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # david tries to vote, but can't - invalid answer
        vote_data['question0'] = 'muahjajaja'
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_BAD_REQUEST, content_type='application/json')

        # david votes correctly
        vote_data['question0'] = 'fo\"o'
        data = self.postAndParse('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_OK, content_type='application/json')
        self.assertTrue('id' in data)
        self.assertEqual(data["is_public"], False)
        self.assertEqual(data["is_direct"], True)
        self.assertEqual(data["is_counted"], True)
        self.assertEqual(data["invalidated_at_date"], None)
        self.assertEqual(data["public_data"], dict())
        first_vote_id = data['id']

        # vote is in cast_votes
        data = self.getAndParse('election/%d/cast_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(data['objects'][0]['id'], first_vote_id)

        # and in direct votes
        data = self.getAndParse('election/%d/direct_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(data['objects'][0]['id'], first_vote_id)

        # david revotes, but making the vote and reason public this time
        vote_data = {
            'is_vote_secret': False,
            'question0': "fo\"o",
            'action': 'vote',
            'reason': "Zy not ye?"
        }
        data = self.postAndParse('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_OK, content_type='application/json')
        self.assertEqual(data["is_public"], True)
        self.assertEqual(data["is_direct"], True)
        self.assertEqual(data["is_counted"], True)
        self.assertEqual(data["reason"], vote_data['reason'])
        self.assertEqual(data["public_data"]['a'], 'vote')
        self.assertEqual(data["public_data"]['answers'],
            [{'a': 'plaintext-answer', 'choices': ['fo"o']}])

        second_vote_id = data['id']

        # old vote is invalidated
        data = self.getAndParse('castvote/%d/' % first_vote_id, code=HTTP_OK)
        self.assertEqual(data["is_public"], False)
        self.assertEqual(data["is_direct"], True)
        self.assertEqual(data["is_counted"], False)
        self.assertTrue(data["invalidated_at_date"] is not None)
        self.assertEqual(data["public_data"], dict())

        # new vote is in cast_votes 
        data = self.getAndParse('election/%d/cast_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 2)
        self.assertEqual(data['objects'][1]['id'], second_vote_id)

        # and in direct votes (and old vote is not because it was invalidated)
        data = self.getAndParse('election/%d/direct_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(data['objects'][0]['id'], second_vote_id)

        # now user1 votes - he is not a member of the agora, so his vote
        # doesn't count. but he can vote, if his vote is public so he acts
        # as a delegate
        self.login('user1', '123')
        vote_data = {
            'is_vote_secret': True,
            'question0': "bar",
            'action': 'vote'
        }
        data = self.postAndParse('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_BAD_REQUEST, content_type='application/json')

        # now try to vote it public - that should work
        vote_data = {
            'is_vote_secret': False,
            'question0': "bar",
            'action': 'vote',
            'reason': "becuase of .. yes"
        }
        data = self.postAndParse('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_OK, content_type='application/json')
        self.assertEqual(data["is_public"], True)
        self.assertEqual(data["is_direct"], True)
        self.assertEqual(data["is_counted"], False)
        self.assertEqual(data["reason"], vote_data['reason'])
        vote3_id = data['id']
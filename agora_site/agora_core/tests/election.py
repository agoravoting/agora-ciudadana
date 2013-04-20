from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase
from django.contrib.markup.templatetags.markup import textile
from datetime import datetime, timedelta
import copy

class ElectionTest(RootTestCase):
    base_election_data = {
        'action': "create_election",
        'pretty_name': "foo bar",
        'description': "foo bar foo bar",
        'questions': [
            {
                'a': 'ballot/question',
                'tally_type': 'ONE_CHOICE',
                'max': 1,
                'min': 0,
                'question': 'Do you prefer foo or bar?',
                'randomize_answer_order': True,
                'answers': [
                    {
                        'a': 'ballot/answer',
                        'url': '',
                        'details': '',
                        'value': 'fo\"o'
                    },
                    {
                        'a': 'ballot/answer',
                        'url': '',
                        'details': '',
                        'value': 'bar'
                    }
                ]
            }
        ],
        'is_vote_secret': True,
        'from_date': '',
        'to_date': '',
    }

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
            set(['admin', 'delete', 'comment', 'create_election', 'delegate']))

    def test_comments(self):
        '''
        Tests adding a comment in the agora
        '''
        # get activity - its empty
        data = self.getAndParse('election/3/comments/')
        comments = data['objects']
        self.assertEqual(len(comments), 0)

        # add a comment as anonymous - fails, forbidden
        orig_data = dict(comment='blah blah blah blah.')
        data = self.post('election/3/add_comment/', orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # still no activity
        data = self.getAndParse('election/3/comments/')
        comments = data['objects']
        self.assertEqual(len(comments), 0)

        # add a comment as a logged in user that is a member of the agora
        self.login('david', 'david')
        data = self.postAndParse('election/3/add_comment/', orig_data,
            code=HTTP_OK, content_type='application/json')

        # now the comment is there
        data = self.getAndParse('election/3/comments/')
        objects = data['objects']
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]['actor']['content_type'], 'user')
        self.assertEqual(objects[0]['actor']['username'], 'david')
        self.assertEqual(objects[0]['action_object']['content_type'], 'comment')
        self.assertEqual(objects[0]['action_object']['comment'], textile(orig_data['comment']))


    def test_change_election(self):
        self.login('user1', '123')
        # user1 creates an election, but remains in requested status
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']
        self.assertEquals(data['pretty_name'], self.base_election_data['pretty_name'])

        # change pretty_name
        orig_data = {
            'pretty_name': "fooooooooooooooo bar"
        }
        data = self.putAndParse('election/%d/' % election_id, data=orig_data,
            content_type='application/json')
        self.assertEquals(data['pretty_name'], orig_data['pretty_name'])

        # change answers
        orig_data = {
            'questions': copy.deepcopy(self.base_election_data['questions'])
        }
        orig_data['questions'][0]['answers'][0]['value'] = "one"
        orig_data['questions'][0]['answers'][1]['value'] = "two"
        orig_data['questions'][0]['answers'].append({
            'a': 'ballot/answer',
            'url': '',
            'details': '',
            'value': 'three'
        })
        data = self.putAndParse('election/%d/' % election_id, data=orig_data,
            content_type='application/json')

        # change answers with one answer > fail
        orig_data['questions'][0]['answers'] = [
            orig_data['questions'][0]['answers'][0]
        ]
        data = self.putAndParse('election/%d/' % election_id, data=orig_data,
            code=HTTP_BAD_REQUEST, content_type='application/json')

        # set start date
        orig_data = {
            'from_date': '2020-02-18T20:13:00'
        }
        data = self.putAndParse('election/%d/' % election_id, data=orig_data,
            content_type='application/json')
        self.assertEquals(orig_data['from_date'], data['voting_starts_at_date'])

    def test_approve_election(self):
        self.login('user1', '123')
        # user1 creates an election, but remains in requested status as it's not
        # an admin
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
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
        orig_data = copy.deepcopy(self.base_election_data)
        orig_data['from_date'] = now
        orig_data['to_date'] = later
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
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
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
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
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

    def test_tally_election(self):
        # create election as admin
        self.login('david', 'david')
        orig_data = copy.deepcopy(self.base_election_data)
        orig_data['questions'][0]['answers'][0]['value'] = "foo"
        orig_data['questions'][0]['answers'][1]['value'] = "bar"
        orig_data['questions'][0]['answers'].append({
            'a': 'ballot/answer',
            'url': '',
            'details': '',
            'value': 'none'
        })
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # all users join the agora
        for username in ['user1', 'user2', 'user3', 'user4', 'user5']:
            self.login(username, '123')
            orig_data = {'action': "join"}
            data = self.post('agora/1/action/', data=orig_data,
                code=HTTP_OK, content_type='application/json')

        vote_foo_data = {
            'is_vote_secret': True,
            'question0': "foo",
            'action': 'vote'
        }
        vote_bar_data = vote_foo_data.copy()
        vote_bar_data['question0'] = "bar"

        cancel_vote_data = dict(action='cancel_vote')

        def delegate(user, password, delegate_id):
            self.login(user, password)
            orig_data = dict(action='delegate_vote', user_id=delegate_id)
            data = self.postAndParse('agora/1/action/', data=orig_data,
                code=HTTP_OK, content_type='application/json')

        def cancel_delegation(user, password):
            self.login(user, password)
            orig_data = dict(action='cancel_vote_delegation')
            data = self.postAndParse('agora/1/action/', data=orig_data,
                code=HTTP_OK, content_type='application/json')

        def vote(usernames, orig_data):
            for username in usernames:
                self.login(username, '123')
                data = self.post('election/%d/action/' % election_id,
                    data=orig_data, code=HTTP_OK,
                    content_type='application/json')

        # vote and delegate
        delegate('david', 'david', 1)
        delegate('user1', '123', 2)
        delegate('user2', '123', 3)
        cancel_delegation('user2', '123')

        vote(['user1', 'user2', 'user3', 'user4'], vote_foo_data)
        vote(['user4', 'user5'], vote_bar_data)
        vote(['user1', 'user3'], cancel_vote_data)

        # This is what happens:
        # 
        # DELEGATIONS:
        # david --> user1
        # user1 --> user2
        # user2 --> user3 CANCELLED
        # 
        # VOTES:
        # david ---> NO VOTE -----------------> delegates > user1 > user2 -> foo
        # user1 ---> foo CANCELLED -----------> delegates > user2 ---------> foo
        # user2 ---> foo --------------------------------------------------> foo
        # user3 ---> foo CANCELLED ----------------------------------------> NO VOTE
        # user4 ---> foo ---> bar OVERWRITTEN -----------------------------> bar
        # user5 ---> bar --------------------------------------------------> bar
        # 
        # Results:
        # foo ---> 3 votes (1 direct, 2 delegated) 
        # bar ---> 2 votes (2 direct, 0 delegated)
        # none --> 0 votes

        # stop election
        self.login('david', 'david')
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # check the tally
        data = self.getAndParse('election/%d/' % election_id)
        result_should_be = {
            'a':'result',
            'delegation_counts':{
                '2':1
            },
            'counts':[
                {
                    'a':'question/result/ONE_CHOICE',
                    'winners': ['foo'],
                    'min':0,
                    'max':1,
                    'tally_type':'ONE_CHOICE',
                    'question':'Do you prefer foo or bar?',
                    'answers':[
                        {
                        'a':'answer/result/ONE_CHOICE',
                        'by_delegation_count':2,
                        'url':u'',
                        'total_count':3,
                        'by_direct_vote_count':1,
                        'value':'foo',
                        'details':u'',
                        'total_count_percentage':60.0
                        },
                        {
                        'a':'answer/result/ONE_CHOICE',
                        'by_delegation_count':0,
                        'url':u'',
                        'total_count':2,
                        'by_direct_vote_count':2,
                        'value':'bar',
                        'details':u'',
                        'total_count_percentage':40.0
                        },
                        {
                        'a':'answer/result/ONE_CHOICE',
                        'by_delegation_count':0,
                        'url':u'',
                        'total_count':0,
                        'by_direct_vote_count':0,
                        'value':'none',
                        'details':u'',
                        'total_count_percentage':0.0
                        }
                    ],
                    'randomize_answer_order':True,
                    'total_votes':5
                }
            ]
        }
        self.assertEqual(data['result'], result_should_be)



    def test_archive_election(self):
        # create election as admin
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
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
        self.assertEqual(data["permissions"], [])

        # because start date has been reset
        data = self.getAndParse('election/%s/' % election_id, code=HTTP_OK)
        self.assertEqual(data['voting_starts_at_date'], None)

    def test_vote_on_election(self):
        # create election as admin
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
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

        # vote appears in votes_from_delegates because it's public
        data = self.getAndParse('election/%d/votes_from_delegates/' %  election_id,
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

        # vote doesn't appear in direct valid votes
        data = self.getAndParse('election/%d/direct_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)

        # but appears in delegate votes because it's public
        data = self.getAndParse('election/%d/votes_from_delegates/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 2)
        self.assertEqual(data['objects'][1]['id'], vote3_id)

    def test_cancel_vote(self):
        # create election as admin
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # vote
        vote_data = {
            'is_vote_secret': False,
            'question0': "bar",
            'action': 'vote',
            'reason': "becuase of .. yes"
        }
        data = self.postAndParse('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_OK, content_type='application/json')
        vote_id = data['id']

        # vote appears in direct votes
        data = self.getAndParse('election/%d/direct_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)

        # cancel the vote
        orig_data = dict(action='cancel_vote')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # vote doesn't appear in direct votes
        data = self.getAndParse('election/%d/direct_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 0)

        # but appears in cast_votes, because there invalid votes are also shown
        data = self.getAndParse('election/%d/cast_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)

        # and vote can be consulted and it's not counted
        data = self.getAndParse('castvote/%d/' % vote_id, code=HTTP_OK)
        self.assertEqual(data["is_public"], True)
        self.assertEqual(data["is_direct"], True)
        self.assertEqual(data["is_counted"], False)
        self.assertTrue(data["invalidated_at_date"] is not None)

        # vote cannot be re-cancelled - there's no active vote
        orig_data = dict(action='cancel_vote')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_BAD_REQUEST, content_type='application/json')

        # user1 joins the agora
        self.login('user1', '123')
        orig_data = dict(action='join')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user1 cannot cancel his vote either, because he didn't vote yet
        orig_data = dict(action='cancel_vote')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_BAD_REQUEST, content_type='application/json')

        # user1 votes
        vote_data = {
            'is_vote_secret': False,
            'question0': "bar",
            'action': 'vote',
            'reason': "becuase of .. yes"
        }
        data = self.postAndParse('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_OK, content_type='application/json')
        vote_id = data['id']

        # vote direct votes
        data = self.getAndParse('election/%d/direct_votes/' %  election_id,
            code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)

        # admin stop the election
        self.login('david', 'david')
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user1 has no permissions to cancel his vote, election stopped
        self.login('user1', '123')
        orig_data = dict(action='cancel_vote')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

    def test_meek_stv(self):
        election_data = {
            'action': "create_election",
            'pretty_name': "foo bar",
            'description': "foo bar foo bar",
            'questions': [
                {
                    'a': 'ballot/question',
                    'tally_type': 'MEEK-STV',
                    'max': 1,
                    'min': 0,
                    'question': 'Who should be the next president?',
                    'randomize_answer_order': True,
                    'num_seats': 2,
                    'answers': [
                        {
                            'a': 'ballot/answer',
                            'url': '',
                            'details': '',
                            'value': 'Florentino'
                        },
                        {
                            'a': 'ballot/answer',
                            'url': '',
                            'details': '',
                            'value': 'Jack'
                        },
                        {
                            'a': 'ballot/answer',
                            'url': '',
                            'details': '',
                            'value': 'Marie'
                        }
                    ]
                }
            ],
            'is_vote_secret': True,
            'from_date': '',
            'to_date': '',
        }

        # create election as admin
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=election_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']

        # start the election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # vote
        def vote(usernames, orig_data):
            for username in usernames:
                self.login(username, '123')
                # join
                join_data = {'action': "join"}
                data = self.post('agora/1/action/', data=join_data,
                    code=HTTP_OK, content_type='application/json')
                # vote
                data = self.post('election/%d/action/' % election_id,
                    data=orig_data, code=HTTP_OK,
                    content_type='application/json')

        vote1_data = {
            'is_vote_secret': False,
            'question0': ["Florentino", "Jack", "Marie"],
            'action': 'vote'
        }
        vote2_data = {
            'is_vote_secret': False,
            'question0': ["Jack", "Marie"],
            'action': 'vote'
        }
        vote(['user1', 'user2', 'user3'], vote1_data)
        vote(['user4', 'user5'], vote2_data)

        # count the votes of the empty election
        self.login('david', 'david')
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        data = self.getAndParse('election/%d/' % election_id)
        results_should_be = {
            'a':'result',
            'delegation_counts':{

            },
            'counts':[
                {
                    'a':'question/result/MEEK-STV',
                    'min':0,
                    'max':1,
                    'tally_type':'MEEK-STV',
                    'question':'Who should be the next president?',
                    'answers':[
                    {
                        'a':'answer/result/MEEK-STV',
                        'url':u'',
                        'total_count':0,
                        'value':'Florentino',
                        'elected':True,
                        'details':u'',
                        'seat_number':1,
                        'total_count_percentage':0
                    },
                    {
                        'a':'answer/result/MEEK-STV',
                        'url':u'',
                        'total_count':0,
                        'value':'Jack',
                        'elected':True,
                        'details':u'',
                        'seat_number':2,
                        'total_count_percentage':0
                    },
                    {
                        'a':'answer/result/MEEK-STV',
                        'url':u'',
                        'total_count':0,
                        'value':'Marie',
                        'elected':False,
                        'details':u'',
                        'seat_number':0,
                        'total_count_percentage':0
                    }
                    ],
                    'winners':[
                        'Florentino',
                        'Jack'
                    ],
                    'num_seats':2,
                    'randomize_answer_order':True,
                    'total_votes':5
                }
            ]
        }
        self.assertEqual(results_should_be, data['result'])
        tally_log_should_be =  [{
            'winners':[
                'Florentino',
                'Jack'
            ],
            'ballots_count':5,
            'dirty_ballots_count':5,
            'candidates':[
                'Florentino',
                'Jack',
                'Marie'
            ],
            'iterations':[
                {
                'exhausted':'0.000000',
                'round_stage':'1',
                'candidates':[
                    {
                        'count':'3.000000',
                        'status':'won',
                        'name':'Florentino',
                        'transfer':False
                    },
                    {
                        'count':'2.000000',
                        'status':'won',
                        'name':'Jack',
                        'transfer':False
                    },
                    {
                        'count':'0.000000',
                        'status':'contesting',
                        'name':'Marie',
                        'transfer':False
                    }
                ]
                }
            ],
            'num_seats':2
        }]
        self.assertEqual(tally_log_should_be, data['extra_data']['tally_log'])

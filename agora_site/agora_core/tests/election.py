# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase
from django.contrib.markup.templatetags.markup import textile
from django.utils import timezone
from datetime import datetime, timedelta
import copy
import hashlib

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
        'security_policy': 'ALLOW_SECRET_VOTING',
        'release_tally_automatically': True,
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
            set(['admin', 'delete', 'comment', 'create_election', 'delegate',
                 'receive_mail']))

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
        self.assertEqual(objects[0]['action_object']['comment'].strip(),
            textile(orig_data['comment']).strip())


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

    def test_freeze_election(self):
        self.login('user1', '123')
        # user1 creates an election, but remains in requested status as it's not
        # an admin
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
            code=HTTP_OK, content_type='application/json')

        self.assertTrue('is_approved' in data)
        self.assertEquals(data['is_approved'], False)
        election_id = data['id']

        # approve election
        self.login('david', 'david')
        orig_data = dict(action='approve')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # has perms to freeze
        orig_data = dict(action='get_permissions')
        data = self.postAndParse('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertTrue('freeze_election' in data["permissions"])

        # freeze election
        self.login('david', 'david')
        orig_data = dict(action='freeze')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

    def test_approve_election2(self):
        self.login('user1', '123')
        # user1 creates an election, but remains in requested status as it's not
        # an admin
        date_format = "%Y/%m/%dT%H:%M:%S"
        now = (timezone.now() + timedelta(seconds=1)).strftime(date_format) + 'Z'
        later = (timezone.now() + timedelta(hours=2)).strftime(date_format) + 'Z'
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

    def test_send_election_results(self):
        # create election as admin
        self.login('david', 'david')
        election_data = self.base_election_data.copy()
        election_data['release_tally_automatically'] = False
        data = self.postAndParse('agora/1/action/', data=election_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # david tries to release results before ending election
        orig_data = dict(action='release_results')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # end the election
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        data = self.getAndParse('election/%d/' % election_id)
        self.assertEqual(data['result'], None)

        # david release results
        orig_data = dict(action='release_results')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        data = self.getAndParse('election/%d/' % election_id)
        self.assertTrue(data['result'] is not None)

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
        for username in ['user1', 'user2', 'user3', 'user4', 'user5', 'user6']:
            self.login(username, '123')
            orig_data = {'action': "join"}
            data = self.post('agora/1/action/', data=orig_data,
                code=HTTP_OK, content_type='application/json')

        vote_foo_data = {
            'is_vote_secret': False,
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
        # one vote in blank
        vote(['user6'], {
            'is_vote_secret': False,
            'question0': "",
            'action': 'vote'
        })


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
        # user6 ---> BLANK VOTE -------------------------------------------> INVALID VOTE
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
                    'dirty_votes':1,
                    'total_votes':5
                }
            ],
            'total_votes': 6,
            'electorate_count': 7,
            'total_delegated_votes': 2
        }



        self.assertEqual(data['result'], result_should_be)
        data = self.getAndParse('delegateelectioncount/?election=%d' % election_id)
        self.check_delegates_counts(data, {
            '2': 2,
            '1': 1
        })

    def check_delegates_counts(self, query, data):
        self.assertEqual(len(data.keys()), query['meta']['total_count'])
        for item in query['objects']:
            del_id = item['delegate'].split('/')[-2]
            self.assertTrue(del_id in data)
            self.assertEqual(data[del_id], item['count'])

    def test_tally_election2(self):
        '''
        This is an election where some delegates vote in secret
        '''

        # make delegated votes secret in this agora
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'security_policy': 'ALLOW_SECRET_VOTING',
                     'biography': "bio",
                     'membership_policy': 'ANYONE_CAN_JOIN',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # create election
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
        for username in ['user1', 'user2', 'user3', 'user4', 'user5', 'user6']:
            self.login(username, '123')
            orig_data = {'action': "join"}
            data = self.post('agora/1/action/', data=orig_data,
                code=HTTP_OK, content_type='application/json')

        vote_foo_data = {
            'is_vote_secret': False,
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
        delegate('user1', '123', 6)
        delegate('user2', '123', 3)

        vote(['user1', 'user3', 'user4'], vote_foo_data)
        vote(['user4', 'user5'], vote_bar_data)
        vote(['user1'], cancel_vote_data)
        # one direct vote in secret
        vote(['user6'], {
            'is_vote_secret': True,
            'question0': "foo",
            'action': 'vote'
        })

        # This is what happens:
        # 
        # DELEGATIONS:
        # david --> user1
        # user1 --> user6
        # user2 --> user3
        # 
        # VOTES:
        # david ---> NO VOTE -----> delegates > user1 delegates secretly --> NO VOTE
        # user1 ---> foo CANCELLED --> delegates > user6, votes secretly --> NO VOTE
        # user2 ---> NO VOTE -----> delegates > user3 > foo ---------------> foo
        # user3 ---> foo --------------------------------------------------> foo
        # user4 ---> foo ---> bar OVERWRITTEN -----------------------------> bar
        # user5 ---> bar --------------------------------------------------> bar
        # user6 ---> foo secretly -----------------------------------------> foo
        # 
        # Results:
        # foo ---> 3 votes (2 direct, 1 delegated) 
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
                        'by_delegation_count':1,
                        'url':u'',
                        'total_count':3,
                        'by_direct_vote_count':2,
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
                    'dirty_votes':0,
                    'total_votes':5
                }
            ],
            'total_votes': 5,
            'electorate_count': 7,
            'total_delegated_votes': 1
        }
        self.assertEqual(data['result'], result_should_be)
        data = self.getAndParse('delegateelectioncount/?election=%d' % election_id)
        self.check_delegates_counts(data, {
            '3':1
        })

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

    def test_archived_election_delisted(self):
        # create election as admin
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # david votes empty vote
        vote_data = {
            'is_vote_secret': True,
            'question0': "bar",
            'action': 'vote'
        }
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_OK, content_type='application/json')

        # stop and tally election
        self.login('david', 'david')
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # check election is listed appropiately as tallied
        data = self.getAndParse('agora/1/tallied_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(data['objects'][0]['id'], election_id)

        # archive the election
        orig_data = dict(action='archive')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # check that election is not listed as tallied anymore
        data = self.getAndParse('agora/1/tallied_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 0)

        # check that election is  listed as archived
        data = self.getAndParse('agora/1/archived_elections/', code=HTTP_OK)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(data['objects'][0]['id'], election_id)

    def test_vote_empty(self):
        # create election as admin
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # david votes empty vote
        vote_data = {
            'is_vote_secret': True,
            'question0': "",
            'action': 'vote'
        }
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_OK, content_type='application/json')

    def test_vote_empty_fail(self):
        # create election as admin
        election_data = self.base_election_data.copy()
        election_data['questions'][0]['min'] = 1
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=self.base_election_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # david votes empty vote, fails - one choice minimum needed
        vote_data = {
            'is_vote_secret': True,
            'question0': "",
            'action': 'vote'
        }
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_BAD_REQUEST, content_type='application/json')

    def test_vote_minmax_stv(self):
        election_data = {
            'action': "create_election",
            'pretty_name': "foo bar",
            'description': "foo bar foo bar",
            'questions': [
                {
                    'a': 'ballot/question',
                    'tally_type': 'MEEK-STV',
                    'max': 2,
                    'min': 2,
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
                        },
                        {
                            'a': 'ballot/answer',
                            'url': '',
                            'details': '',
                            'value': 'Jijoe'
                        },
                    ]
                }
            ],
            'security_policy': 'ALLOW_SECRET_VOTING',
            'from_date': '',
            'to_date': '',
        }
        # create election as admin
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=election_data,
            code=HTTP_OK, content_type='application/json')
        election_id = data['id']

        # start election
        orig_data = dict(action='start')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # david tries to vote empty but fails, need to choose at least one
        vote_data = {
            'is_vote_secret': True,
            'question0': [],
            'action': 'vote'
        }
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_BAD_REQUEST, content_type='application/json')

        # david votes to one and two options and works fine
        vote_data ['question0'] = ['Jijoe']
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_BAD_REQUEST, content_type='application/json')

        vote_data ['question0'] = ['Marie', 'Jack']
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_OK, content_type='application/json')

        # david tries to vote to 3 options and fails, too many
        vote_data ['question0'] = ['Marie', 'Jack', 'Florentino']
        data = self.post('election/%d/action/' % election_id,
            data=vote_data, code=HTTP_BAD_REQUEST, content_type='application/json')


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
            'reason': "<p>Zy not ye?</p>"
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
            'reason': "<p>becuase of .. yes</p>"
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
            'release_tally_automatically': True,
            'questions': [
                {
                    'a': 'ballot/question',
                    'tally_type': 'MEEK-STV',
                    'max': 3,
                    'min': 0,
                    'question': 'Who should be the next presidentá unicode chars ñè?',
                    'randomize_answer_order': True,
                    'num_seats': 2,
                    'answers': [
                        {
                            'a': 'ballot/answer',
                            'url': '',
                            'details': '',
                            'value': u'Florentino de los Jagüeños jórl!'
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
            'security_policy': 'ALLOW_SECRET_VOTING',
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
            'question0': [u'Florentino de los Jagüeños jórl!', "Jack", "Marie"],
            'action': 'vote'
        }
        vote2_data = {
            'is_vote_secret': False,
            'question0': ["Jack", "Marie"],
            'action': 'vote'
        }
        vote(['user1', 'user2', 'user3'], vote1_data)
        vote(['user4', 'user5'], vote2_data)
        # one vote in blank
        vote(['user6'], {
            'is_vote_secret': False,
            'question0': [],
            'action': 'vote'
        })

        # count the votes of the empty election
        self.login('david', 'david')
        orig_data = dict(action='stop')
        data = self.post('election/%d/action/' % election_id, data=orig_data,
            code=HTTP_OK, content_type='application/json')
        data = self.getAndParse('election/%d/' % election_id)
        results_should_be = {
            'a':'result',
            'counts':[
                {
                    'a':'question/result/MEEK-STV',
                    'min':0,
                    'max':3,
                    'tally_type':'MEEK-STV',
                    'question': 'Who should be the next presidentá unicode chars ñè?',
                    'answers':[
                    {
                        'a':'answer/result/MEEK-STV',
                        'url':u'',
                        'total_count':0,
                        'value':u'Florentino de los Jagüeños jórl!',
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
                        u'Florentino de los Jagüeños jórl!',
                        'Jack'
                    ],
                    'num_seats':2,
                    'randomize_answer_order':True,
                    'dirty_votes':1,
                    'total_votes':5
                }
            ],
            'total_votes': 6,
            'electorate_count': 7,
            'total_delegated_votes': 0
        }
        self.assertEqual(results_should_be, data['result'])
        tally_log_should_be =  [{
            'winners':[
                u'Florentino de los Jagüeños jórl!',
                'Jack'
            ],
            'ballots_count':5,
            'dirty_ballots_count':6,
            'candidates':[
                u'Florentino de los Jagüeños jórl!',
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
                        'name':u'Florentino de los Jagüeños jórl!',
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
        data = self.getAndParse('election/%d/extra_data/' % election_id)
        self.assertEqual(tally_log_should_be, data['tally_log'])

    def test_broken_loop_delegation(self):
        '''
        tests that when A delegates in B and B in A, this doesn't brick the
        election tally. Just those votes are not counted
        '''

        # make delegated votes secret in this agora
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'security_policy': 'ALLOW_SECRET_VOTING',
                     'biography': "bio",
                     'membership_policy': 'ANYONE_CAN_JOIN',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # create election
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
        for username in ['user1', 'user2', 'user3', 'user4', 'user5', 'user6']:
            self.login(username, '123')
            orig_data = {'action': "join"}
            data = self.post('agora/1/action/', data=orig_data,
                code=HTTP_OK, content_type='application/json')

        vote_foo_data = {
            'is_vote_secret': False,
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
        delegate('user2', '123', 0)
        delegate('user4', '123', 5)

        vote(['user3'], vote_foo_data)
        vote(['user5', 'user6'], vote_bar_data)

        # This is what happens:
        # 
        # DELEGATIONS:
        # david --> user1 --> user2 --> david (broken loop)
        # user4 --> user5
        # 
        # VOTES:
        # david ---> NO VOTE -----> broken delegation chain --> NO VOTE
        # user1 ---> NO VOTE -----> broken delegation chain --> NO VOTE
        # user2 ---> NO VOTE -----> broken delegation chain --> NO VOTE
        # user3 ---> foo --------------------------------------------------> foo
        # user4 ---> NO VOTE -----> user5 > bar ---------------------------> bar
        # user5 ---> bar --------------------------------------------------> bar
        # user6 ---> bar --------------------------------------------------> bar
        # 
        # Results:
        # foo ---> 1 votes (1 direct, 0 delegated) 
        # bar ---> 3 votes (2 direct, 1 delegated)
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
            'counts':[
                {
                    'a':'question/result/ONE_CHOICE',
                    'winners': ['bar'],
                    'min':0,
                    'max':1,
                    'tally_type':'ONE_CHOICE',
                    'question':'Do you prefer foo or bar?',
                    'answers':[
                        {
                        'a':'answer/result/ONE_CHOICE',
                        'by_delegation_count':0,
                        'url':u'',
                        'total_count':1,
                        'by_direct_vote_count':1,
                        'value':'foo',
                        'details':u'',
                        'total_count_percentage':25.0
                        },
                        {
                        'a':'answer/result/ONE_CHOICE',
                        'by_delegation_count':1,
                        'url':u'',
                        'total_count':3,
                        'by_direct_vote_count':2,
                        'value':'bar',
                        'details':u'',
                        'total_count_percentage':75.0
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
                    'dirty_votes':0,
                    'total_votes':4
                }
            ],
            'total_votes': 4,
            'electorate_count': 7,
            'total_delegated_votes': 1
        }
        self.assertEqual(data['result'], result_should_be)
        data = self.getAndParse('delegateelectioncount/?election=%d' % election_id)
        self.check_delegates_counts(data, {
            '5':1
        })

    def test_check_proof_of_knowledge(self):
        '''
        Demonstrates how to check a proof of knowledge in python
        '''
        pk = {
            "g":"27257469383433468307851821232336029008797963446516266868278476598991619799718416119050669032044861635977216445034054414149795443466616532657735624478207460577590891079795564114912418442396707864995938563067755479563850474870766067031326511471051504594777928264027177308453446787478587442663554203039337902473879502917292403539820877956251471612701203572143972352943753791062696757791667318486190154610777475721752749567975013100844032853600120195534259802017090281900264646220781224136443700521419393245058421718455034330177739612895494553069450438317893406027741045575821283411891535713793639123109933196544017309147",
            "p":"49585549017473769285737299189965659293354088286913371933804180900778253856217662802521113040825270214021114944067918826365443480688403488878664971371922806487664111406970012663245195033428706668950006712214428830267861043863002671272535727084730103068500694744742135062909134544770371782327891513041774499809308517270708450370367766144873413397605830861330660620343634294061022593630276805276836395304145517051831281606133359766619313659042006635890778628844508225693978825158392000638704210656475473454575867531351247745913531003971176340768343624926105786111680264179067961026247115541456982560249992525766217307447",
            "q":"24792774508736884642868649594982829646677044143456685966902090450389126928108831401260556520412635107010557472033959413182721740344201744439332485685961403243832055703485006331622597516714353334475003356107214415133930521931501335636267863542365051534250347372371067531454567272385185891163945756520887249904654258635354225185183883072436706698802915430665330310171817147030511296815138402638418197652072758525915640803066679883309656829521003317945389314422254112846989412579196000319352105328237736727287933765675623872956765501985588170384171812463052893055840132089533980513123557770728491280124996262883108653723",
            "y":"5383828687359633175167457781427171576794341933360862666155699443683378093084067322903153909147869270211909454109000037475463711858090937817089961996669436360851680043753399404247503586121519408689243902503807397936894430865478995603463706199441782503092456174491724912183336291543925768465738374804119979063155224354863963479242893806899154444635140493973491312715232651159541959188269501075455784792308595852813494423957501209842189151915522785324453109666734268519076890243666667963167602354494027277713699715567395330819944696895738803312321891165392405018562486913974801163499309171266032895339543830269614771098"};

        ballot = {
            "ciphertext": {
                "alpha":"37754136675800482853401255670222166873136041449784053169347450203228963401110272352067231222448121872615934054987027030670549433809795094942335168453321362412866901987302897761457084844158682479171001903552859547962721676924755481649929580548836484328764269841601891790749345900298361352893272252418820245072114345783763815981635193490687689398196315655251448289084615541981996178621423523743906032504065709472233393370801220063104954174597329715200859558524045727076293254825914693623866082694836112114120727674878249703317361283652836922491430477584000838263598786371033886418298974247895442032716367749834814884142",
                "beta":"43456542993260763958635630595509431070051689482966537974040206907315421370393072967613777109781057932670186131037066743263087355846041171635152028200927263881597703277077271777676024357655290847731008595518418213252682830692860862727893930397309973535438661363760361977287101848848386293677277633986625663457170151788684885937994705107025513765508657779164994225981201849722337182053279450327292963041881335696997062959516383161030607515249947240024792334062381474552270177612827170241327345247530114488208633672483694633526427874738996242709070283618648678992874182784663843663080064090331724033039670950454908187081"
            },
            "proof": {
                "challenge":"71024943723290224299152410715097278157351334607535280633900722130386444357811",
                "commitment":"38059035652794057606346510759432685857084045292689853647721769906573064856104062137496870009233293820583508285786293016593933019830150773531431292507653918298378084591602843429412564815254955042209329388578781897353095601394610290057613509248040647877679608645226806980826370815984377306317558823334123717217540219018393314485396470227647725528502251122799046022503302558824683995767840896147369879418836719142355500250009656264805047142096798693187527372865198888689649847263737982483571991289420345554334891933310972494828422243460876121794690255892096150227695845398033552240188046021232677158001218120316412051625",
                "response":"13691685358133574480898319736517081144234463016814164908173537450611727361657115017168713076161264952793941972349043765040017720143330617590976176399243357811788287497150375412352140512762779709072163426420392087522441811512711693003018026512303094652251078764254210725378999849223359676344080490460176042172270808431764655651611317943195737483417788003493275476539153566823294346932059516476238915602041756724895423815174558062231079410650980749154005030770940399614703230740834750155648645708438814706018919007567043371142211929921475174656499442321683631884981870338989660977943899516010681069949129923327452627725"
            }
        }

        pk_p = int(pk['p'])
        pk_g = int(pk['g'])
        commitment = int(ballot['proof']['commitment'])
        response = int(ballot['proof']['response'])
        challenge =  int(ballot['proof']['challenge'])
        alpha = int(ballot['ciphertext']['alpha'])

        # verify the challenge is valid
        hash = hashlib.sha256()
        hash.update(str(commitment))
        challenge_calculated = int(hash.hexdigest(), 16)
        assert challenge_calculated == challenge

        first_part = pow(pk_g, response, pk_p)
        second_part = (commitment * pow(alpha, challenge, pk_p)) % pk_p

        #// check g^response == commitment * (g^t) ^ challenge == commitment * (alpha) ^ challenge
        assert first_part == second_part


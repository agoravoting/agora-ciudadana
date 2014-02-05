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
from uuid import uuid4
import copy

class DelegateElectionCountTest(RootTestCase):
    base_election_data = {
        'action': "create_election",
        'pretty_name': "foo bar",
        'description': "foo bar foo bar",
        'questions': [
            {
                'a': 'ballot/question',
                'tally_type': 'ONE_CHOICE',
                'layout': 'SIMPLE',
                'max': 1,
                'min': 0,
                'question': 'Do you prefer foo or bar?',
                'randomize_answer_order': True,
                'answers': [
                    {
                        'a': 'ballot/answer',
                        'details': '',
                        'value': 'fo\"o'
                    },
                    {
                        'a': 'ballot/answer',
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

    def test_list(self):
        # create election as admin
        self.login('david', 'david')
        orig_data = copy.deepcopy(self.base_election_data)
        orig_data['questions'][0]['answers'][0]['value'] = "foo"
        orig_data['questions'][0]['answers'][1]['value'] = "bar"
        orig_data['questions'][0]['answers'].append({
            'a': 'ballot/answer',
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
                orig_data['unique_randomness'] = str(uuid4())
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
                    'layout': 'SIMPLE',
                    'question':'Do you prefer foo or bar?',
                    'answers':[
                        {
                        'a':'answer/result/ONE_CHOICE',
                        'by_delegation_count':2,
                        'total_count':3,
                        'by_direct_vote_count':1,
                        'value':'foo',
                        'details':u'',
                        'total_count_percentage':60.0
                        },
                        {
                        'a':'answer/result/ONE_CHOICE',
                        'by_delegation_count':0,
                        'total_count':2,
                        'by_direct_vote_count':2,
                        'value':'bar',
                        'details':u'',
                        'total_count_percentage':40.0
                        },
                        {
                        'a':'answer/result/ONE_CHOICE',
                        'by_delegation_count':0,
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
        data = self.getAndParse('delegateelectioncount/?election__agora=1')
        self.check_delegates_counts(data, {
            '2': 2,
            '1': 1
        })
        data = self.getAndParse('delegateelectioncount/?election__agora=2')
        self.check_delegates_counts(data, {})

    def check_delegates_counts(self, query, data):
        self.assertEqual(len(data.keys()), query['meta']['total_count'])
        for item in query['objects']:
            del_id = item['delegate'].split('/')[-2]
            self.assertTrue(del_id in data)
            self.assertEqual(data[del_id], item['count'])

from django.utils import unittest
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.utils import simplejson
from itertools import *
import json


# FIXME better url treatment
# FIXME relying on ordering when doing api set calls
# FIXME should construct data through posts

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(AgoraTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(UserTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(MiscTest))
    return suite

API_ROOT = '/api/v1/'

class RootTestCase(TestCase):
    fixtures = ['test_users.json', 'test_agoras.json']

    def login(self, user, passw):
        loggedIn = self.client.login(username=user, password=passw)
        self.assertTrue(loggedIn)

    def get(self, url, code = 200):
        response = self.client.get(API_ROOT + url)
        self.assertEqual(response.status_code, code)

        return response.content

    def getAndParse(self, url, code = 200):
        json = self.get(url, code)
        data = simplejson.loads(json)

        return data

    def post(self, url, data = {}, code = 200, **kwargs):
        response = self.client.post(API_ROOT + url, data, **kwargs)
        self.assertEqual(response.status_code, code)

        return response.content

    def postAndParse(self, url, data = {}, code = 200, **kwargs):
        json = self.post(url, data, code, **kwargs)
        data = simplejson.loads(json)

        return data

    def delete(self, url, data = {}, code = 200, **kwargs):
        response = self.client.delete(API_ROOT + url, data, **kwargs)
        self.assertEqual(response.status_code, code)

        return response.content

    def deleteAndParse(self, url, data = {}, code = 200, **kwargs):
        json = self.delete(url, data, code, **kwargs)
        data = simplejson.loads(json)

        return data

    def put(self, url, data = {}, code = 200, **kwargs):
        response = self.client.put(API_ROOT + url, data, **kwargs)
        self.assertEqual(response.status_code, code)

        return response.content

    def putAndParse(self, url, data = {}, code = 200, **kwargs):
        json = self.put(url, data, code, **kwargs)
        data = simplejson.loads(json)

        return data


class AgoraTest(RootTestCase):
    def test_agora(self):
        # all
        data = self.getAndParse('agora/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 2)

    def test_agora_find(self):
        # find
        data = self.getAndParse('agora/1/')
        self.assertEquals(data['name'], 'agoraone')

        data = self.getAndParse('agora/2/')
        self.assertEquals(data['name'], 'agoratwo')

        data = self.get('agora/200/', 404)

    def test_agora_creation(self):
        # creating agora
        self.login('david', 'david')
        orig_data = {'pretty_name': 'created agora',
                     'short_description': 'created agora description',
                     'is_vote_secret': False}
        data = self.postAndParse('agora/', json.dumps(orig_data), 201,
                                 content_type='application/json')
        self.assertEqual(data['pretty_name'], 'created agora')

        data = self.getAndParse('agora/%s/' % data['id'])
        for k, v in orig_data.items():
            self.assertEquals(data[k], v)

    def test_agora_deletion(self):
        # TODO check permissions
        self.login('david', 'david')
        data = self.getAndParse('agora/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 2)

        self.delete('agora/1/', {}, 204)

        data = self.getAndParse('agora/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 1)

        self.delete('agora/1/', {}, 404)
        self.delete('agora/200/', {}, 404)

    def test_agora_update(self):
        # TODO check permissions
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'is_vote_secret': False,
                     'biography': "bio",
                     'membership_policy': 'ANYONE_CAN_JOIN',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.putAndParse('agora/1/', json.dumps(orig_data), 202,
                                 content_type='application/json')

        data = self.getAndParse('agora/1/')
        for k, v in orig_data.items():
            self.assertEquals(data[k], v)


class CastVoteTest(RootTestCase):
    # TODO
    pass

class ElectionTest(RootTestCase):
    # TODO
    pass

class FollowTest(RootTestCase):
    # TODO
    pass

class ActionTest(RootTestCase):
    # TODO
    pass

class UserTest(RootTestCase):

    def powerset(self, iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

    def merge(self, a, b): return dict(a.items() + b.items())

    def test_user(self):
        # all
        data = self.getAndParse('user/')
        users = data['objects']
        # 7 = 5 test users, + admin + anonymous
        self.assertEqual(len(users), 7)

        # find
        data = self.getAndParse('user/0/')
        self.assertEquals(data['username'], 'david')

        data = self.getAndParse('user/1/')
        self.assertEquals(data['username'], 'user1')
        self.assertEquals(data['first_name'], 'Juana Molero')

        data = self.get('user/200/', 404)

        # set
        data = self.getAndParse('user/set/1;3/')
        self.assertEqual(len(data['objects']), 2)
        self.assertEquals(data['objects'][0]['username'], 'user1')
        self.assertEquals(data['objects'][1]['username'], 'user3')

        data = self.getAndParse('user/set/400;3/')
        self.assertEqual(data['not_found'][0], '400')
        self.assertEqual(len(data['objects']), 1)
        self.assertEquals(data['objects'][0]['username'], 'user3')

        data = self.getAndParse('user/set/400;300/')
        self.assertEqual(data['not_found'][0], '400')
        self.assertEqual(data['not_found'][1], '300')
        self.assertEqual(len(data['objects']), 0)

        data = self.get('user/set/', 404)

    def test_user_settings(self):
        self.login('david', 'david')
        data = self.getAndParse('user/settings/')

        self.assertEqual(data['username'], 'david')
        # TODO, testing via PUT, not yet implemented in user.py

    def test_user_set_username(self):
        data = self.get('user/set_username/', 404)
        data = self.getAndParse('user/set_username/david;user1/')
        self.assertEqual(len(data['objects']), 2)
        self.assertEquals(data['objects'][0]['username'], 'david')
        self.assertEquals(data['objects'][1]['username'], 'user1')

        data = self.getAndParse('user/set_username/david;bogus/')
        self.assertEqual(len(data['objects']), 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

        data = self.get('user/set_username/', 404)

    def test_password_reset(self):
        data = self.postAndParse('user/password_reset/')
        self.assertEqual(data['status'], 'failed')
        data = self.postAndParse('user/password_reset/', {'email': 'hohoho'})
        self.assertEqual(data['status'], 'failed')
        data = self.postAndParse('user/password_reset/', {'email': 'hohoho@hohoho.com'})
        self.assertEqual(data['status'], 'failed')
        data = self.postAndParse('user/password_reset/', {'email': 'david@david.com'})
        self.assertEqual(data['status'], 'success')
        # TODO can we test that the operation worked?

    # register api call throws error causing this test to fail
    def test_register(self):
        from django.core.management import call_command

        # creates permissions tables needed by userna to create users
        # for more info look at
        # http://docs.django-userena.org/en/latest/faq.html#i-get-a-permission-matching-query-does-not-exist-exception
        call_command('check_permissions', verbosity=0, interactive=False)

        # test 2^4 combinations
        ps = self.powerset([{'email': 'hohoho@hoho.com'}, {'password1': 'hello'}, {'password2': 'hello'}, {'username': 'username'}])
        for i in ps:
            params = {}
            if(len(i) > 0):
                params = reduce(self.merge, i)

            data = self.postAndParse('user/register/', params)
            if(len(i) == 4):
                self.assertEqual(data['status'], 'success')
            else:
                self.assertEqual(data['status'], 'failed')

        # bad email
        data = self.postAndParse('user/register/', {'email': 'hoho.com', 'password1': 'hello', 'password1': 'hello2', 'username': 'username'})
        self.assertEqual(data['status'], 'failed')
        # password mismatch
        data = self.postAndParse('user/register/', {'email': 'hohoho@hoho.com', 'password1': 'hello', 'password2': 'hello2', 'username': 'username'})
        self.assertEqual(data['status'], 'failed')

    def test_login(self):
        "Test that the api call login works"
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['id'], '-1')
        data = self.postAndParse('user/login/', {'identification': 'david', 'password': 'david'})
        self.assertEqual(data['status'], 'success')
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['username'], 'david')

    def test_logout(self):
        "Test that the api call logout works"
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['id'], '-1')
        data = self.postAndParse('user/login/', {'identification': 'david', 'password': 'david'})
        self.assertEqual(data['status'], 'success')
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['username'], 'david')
        data = self.postAndParse('user/logout/')
        self.assertEqual(data['status'], 'success')
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['id'], '-1')

    # argless call error causes this test to fail
    def test_username_available(self):
        data = self.getAndParse('user/username_available/?username=asdasd')
        self.assertEqual(data['status'], 'success')
        data = self.getAndParse('user/username_available/?username=david')
        self.assertEqual(data['status'], 'failed')


class MiscTest(RootTestCase):
    def test_login(self):
        "Test that the django test client log in works"
        self.login('david', 'david')
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['username'], 'david')

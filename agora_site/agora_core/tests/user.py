from itertools import chain, combinations

from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase


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

        data = self.get('user/200/', code=HTTP_NOT_FOUND)

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

        data = self.get('user/set/', code=HTTP_NOT_FOUND)

    def test_user_settings(self):
        self.login('david', 'david')
        data = self.getAndParse('user/settings/')

        self.assertEqual(data['username'], 'david')
        # TODO, testing via PUT, not yet implemented in user.py

    def test_user_set_username(self):
        data = self.get('user/set_username/', code=HTTP_NOT_FOUND)
        data = self.getAndParse('user/set_username/david;user1/')
        self.assertEqual(len(data['objects']), 2)
        self.assertEquals(data['objects'][0]['username'], 'david')
        self.assertEquals(data['objects'][1]['username'], 'user1')

        data = self.getAndParse('user/set_username/david;bogus/')
        self.assertEqual(len(data['objects']), 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

        data = self.get('user/set_username/', code=HTTP_NOT_FOUND)

    def test_password_reset(self):
        data = self.postAndParse('user/password_reset/', code=HTTP_BAD_REQUEST)
        data = self.postAndParse('user/password_reset/', {'email': 'hohoho'},
            code=HTTP_BAD_REQUEST)
        data = self.postAndParse('user/password_reset/',
        {'email': 'hohoho@hohoho.com'}, code=HTTP_BAD_REQUEST)
        data = self.postAndParse('user/password_reset/', {'email': 'david@david.com'})
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

            if(len(i) == 4):
                data = self.postAndParse('user/register/', params, code=HTTP_OK)
            else:
                data = self.postAndParse('user/register/', params,
                    code=HTTP_BAD_REQUEST)

        # bad email
        data = self.postAndParse('user/register/',
            {
                'email': 'hoho.com',
                'password1': 'hello',
                'password1': 'hello2',
                'username': 'username'
            }, code=HTTP_BAD_REQUEST)


        # password mismatch
        data = self.postAndParse('user/register/',
            {
                'email': 'hohoho@hoho.com',
                'password1': 'hello',
                'password2': 'hello2',
                'username': 'username'
            }, code=HTTP_BAD_REQUEST)


    def test_login(self):
        """
        Test that the api call login works
        """

        data = self.getAndParse('user/settings/')
        self.assertEqual(data['id'], -1)
        data = self.postAndParse('user/login/',
            {'identification': 'david', 'password': 'david'})

        data = self.getAndParse('user/settings/')
        self.assertEqual(data['username'], 'david')

    def test_logout(self):
        """
        Test that the api call logout works
        """
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['id'], -1)
        data = self.post('user/login/',
            {'identification': 'david', 'password': 'david'})
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['username'], 'david')

        data = self.postAndParse('user/logout/')

        data = self.getAndParse('user/settings/')
        self.assertEqual(data['id'], -1)

    # argless call error causes this test to fail
    def test_username_available(self):
        data = self.getAndParse('user/username_available/?username=asdasd')
        data = self.getAndParse('user/username_available/?username=david',
            code=HTTP_BAD_REQUEST);

    def test_agoras(self):
        # not logged in, needs to be logged in to get agoras
        self.get('user/agoras/', code=HTTP_FORBIDDEN)

        self.login('david', 'david')
        data = self.getAndParse('user/agoras/')
        self.assertEqual(len(data["objects"]), 2)

        self.login('user1', '123')
        data = self.getAndParse('user/agoras/')
        self.assertEqual(len(data["objects"]), 0)

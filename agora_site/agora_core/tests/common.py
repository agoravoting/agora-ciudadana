from django.test import TestCase
from django.utils import simplejson


API_ROOT = '/api/v1/'
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405

class RootTestCase(TestCase):
    fixtures = ['test_users.json',
                'test_agoras.json',
                'test_elections.json',
                'test_authorities.json']

    def login(self, user, passw):
        loggedIn = self.client.login(username=user, password=passw)
        self.assertTrue(loggedIn)

    def get(self, url, code=HTTP_OK):
        response = self.client.get(API_ROOT + url)
        self.assertEqual(response.status_code, code)

        return response.content

    def getAndParse(self, url, code=HTTP_OK):
        json = self.get(url, code)
        data = simplejson.loads(json)

        return data

    def post(self, url, data = {}, code=HTTP_OK,
        content_type='application/json', **kwargs):

        response = self.client.post(API_ROOT + url, simplejson.dumps(data),
            content_type=content_type, **kwargs)
        self.assertEqual(response.status_code, code)

        return response.content

    def postAndParse(self, url, data = {}, code=HTTP_OK,
        content_type='application/json', **kwargs):

        json = self.post(url, data, code, content_type=content_type, **kwargs)
        data = simplejson.loads(json)

        return data

    def delete(self, url, data = {}, code=HTTP_NO_CONTENT, **kwargs):
        response = self.client.delete(API_ROOT + url, data,
            **kwargs)
        self.assertEqual(response.status_code, code)

        return response.content

    def deleteAndParse(self, url, data = {}, code=HTTP_NO_CONTENT, **kwargs):
        json = self.delete(url, data, code, **kwargs)
        data = simplejson.loads(json)

        return data

    def put(self, url, data = {}, code=HTTP_ACCEPTED, content_type='application/json',
        **kwargs):
        response = self.client.put(API_ROOT + url, simplejson.dumps(data),
            content_type=content_type, **kwargs)
        self.assertEqual(response.status_code, code)

        return response.content

    def putAndParse(self, url, data = {}, code=HTTP_ACCEPTED, **kwargs):
        json = self.put(url, data, code, **kwargs)
        data = simplejson.loads(json)

        return data

    def assertDictContains(self, a, b):
        '''
        Assert true when a contains b and both are dicts
        '''
        for k, v in b.iteritems():
            assert k in a and v == b[k]

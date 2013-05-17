from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND,
                    HTTP_METHOD_NOT_ALLOWED)

from common import RootTestCase
from django.core import management


class SearchTest(RootTestCase):

    def setUp(self):
        management.call_command('rebuild_index', verbosity=0, interactive=False)

    def test_search(self):
        # all
        data = self.getAndParse('search/')
        self.assertEquals(data['meta']['total_count'], 15)

        import ipdb, json; ipdb.set_trace()
        data = self.getAndParse('search/?q=agoraone')
        self.assertEquals(data['meta']['total_count'], 3)

    def test_search_agora(self):
        data = self.getAndParse('search/?model=agora')
        self.assertEquals(data['meta']['total_count'], 2)

        data = self.getAndParse('search/?model=agora&q=agoraone')
        self.assertEquals(data['meta']['total_count'], 1)

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

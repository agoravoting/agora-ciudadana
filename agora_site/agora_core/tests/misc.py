from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase


class MiscTest(RootTestCase):
    def test_login(self):
        """
        Test that the django test client log in works
        """
        self.login('david', 'david')
        data = self.getAndParse('user/settings/')
        self.assertEqual(data['username'], 'david')

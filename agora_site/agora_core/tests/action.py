from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase
from agora_site.agora_core.tasks.agora import send_request_membership_mails
from django.contrib.sites.models import Site

class ActionTest(RootTestCase):
    def test_agora(self):
        data = self.getAndParse('action/agora/1/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 0)

        orig_data = {'comment': 'blah blah blah blah.'}
        # not logged in
        data = self.post('action/agora/1/add_comment/', orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        data = self.getAndParse('action/agora/1/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 0)

        self.login('david', 'david')
        data = self.postAndParse('action/agora/1/add_comment/', orig_data,
            code=HTTP_OK, content_type='application/json')

        data = self.getAndParse('action/agora/1/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 1)
        self.assertEqual(agoras[0]['actor']['content_type'], 'user')
        self.assertEqual(agoras[0]['actor']['username'], 'david')
        self.assertEqual(agoras[0]['action_object']['content_type'], 'comment')
        self.assertEqual(agoras[0]['action_object']['comment'], orig_data['comment'])

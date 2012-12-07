from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND)

from common import RootTestCase


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

        data = self.get('agora/200/', code=HTTP_NOT_FOUND)

    def test_agora_creation(self):
        # creating agora
        self.login('david', 'david')
        orig_data = {'pretty_name': 'created agora',
                     'short_description': 'created agora description',
                     'is_vote_secret': False}
        data = self.postAndParse('agora/', orig_data,
            code=HTTP_CREATED, content_type='application/json')

        data = self.getAndParse('agora/%s/' % data['id'])
        for k, v in orig_data.items():
            self.assertEquals(data[k], v)

    def test_agora_deletion(self):
        self.login('david', 'david')
        data = self.getAndParse('agora/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 2)

        self.delete('agora/1/', code=HTTP_NO_CONTENT)

        data = self.getAndParse('agora/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 1)

        # check permissions
        self.login('user1', '123')
        self.delete('agora/2/', code=HTTP_FORBIDDEN)
        self.login('david', 'david')
        self.delete('agora/2/', code=HTTP_NO_CONTENT)
        self.delete('agora/2/', {}, code=HTTP_NOT_FOUND)

        data = self.getAndParse('agora/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 0)

        self.delete('agora/1/', {}, code=HTTP_NOT_FOUND)
        self.delete('agora/200/', {}, code=HTTP_NOT_FOUND)

    def test_agora_update(self):
        # TODO check permissions
        self.login('user1', '123')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'is_vote_secret': False,
                     'biography': "bio",
                     'membership_policy': 'ANYONE_CAN_JOIN',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')
        self.login('david', 'david')
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        data = self.getAndParse('agora/1/')
        for k, v in orig_data.items():
            self.assertEquals(data[k], v)



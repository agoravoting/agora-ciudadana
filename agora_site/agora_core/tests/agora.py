from common import (HTTP_OK,
                    HTTP_CREATED,
                    HTTP_ACCEPTED,
                    HTTP_NO_CONTENT,
                    HTTP_BAD_REQUEST,
                    HTTP_FORBIDDEN,
                    HTTP_NOT_FOUND,
                    HTTP_METHOD_NOT_ALLOWED)

from common import RootTestCase
from agora_site.agora_core.tasks.agora import send_request_membership_mails
from django.contrib.sites.models import Site

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

    def test_agora_request_membership(self):
        self.login('user1', '123')
        orig_data = {'action': "request_membership", }
        # User cannot request membership; he can directly join instead
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        orig_data = {'action': "join", }
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # setting restricted joining policy
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'is_vote_secret': False,
                     'biography': "bio",
                     'membership_policy': 'JOINING_REQUIRES_ADMINS_APPROVAL',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        orig_data = {'action': "request_membership", }
        # user is already a member of this agora
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # Noone is requesting
        data = self.postAndParse('agora/1/membership_requests/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 0)

        self.login('user2', '123')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user already requested membership
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # user2 is requesting
        data = self.postAndParse('agora/1/membership_requests/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'user2')

    def test_agora_accept_membership_request(self):
        '''
        Test that an admin can accept a membership request
        '''

        # setting restricted joining policy
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'is_vote_secret': False,
                     'biography': "bio",
                     'membership_policy': 'JOINING_REQUIRES_ADMINS_APPROVAL',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # requesting membership
        self.login('user2', '123')
        orig_data = dict(action='request_membership')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # trying to accept membership with an user with no permissions,
        # should fail
        self.login('user1', '123')
        orig_data = dict(action='accept_membership', username='user2')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # user2 is still requesting
        data = self.postAndParse('agora/1/membership_requests/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'user2')

        # and user2 is not a member
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

        # accept membership properly, should succeed
        self.login('david', 'david')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user2 is not requesting any more
        data = self.postAndParse('agora/1/membership_requests/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 0)

        # user2 is a member now
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 2)
        self.assertEquals(data['objects'][1]['username'], 'user2')

    def test_agora_deny_membership_request(self):
        '''
        Test that an admin can accept a membership request
        '''

        # setting restricted joining policy
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'is_vote_secret': False,
                     'biography': "bio",
                     'membership_policy': 'JOINING_REQUIRES_ADMINS_APPROVAL',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # requesting membership
        self.login('user2', '123')
        orig_data = dict(action='request_membership')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # trying to deny membership with an user with no permissions,
        # should fail
        self.login('user1', '123')
        orig_data = dict(action='deny_membership', username='user2')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # user2 is still requesting
        data = self.postAndParse('agora/1/membership_requests/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'user2')

        # and user2 is not a member
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

        # deny membership properly, should succeed
        self.login('david', 'david')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user2 is not requesting any more
        data = self.postAndParse('agora/1/membership_requests/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 0)

        # and user2 is not a member
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

    def test_agora_add_membership1(self):
        '''
        Test that an admin can add a member
        '''

        # setting restricted joining policy
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'is_vote_secret': False,
                     'biography': "bio",
                     'membership_policy': 'JOINING_REQUIRES_ADMINS_APPROVAL',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # requesting membership
        self.login('user2', '123')
        orig_data = dict(action='request_membership')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # trying to add member with an user with no permissions,
        # should fail
        self.login('user1', '123')
        orig_data = dict(action='add_membership', username='user2',
            welcome_message="weeEeEeelcome!")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # user2 is still requesting
        data = self.postAndParse('agora/1/membership_requests/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'user2')

        # and user2 is not a member
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

        # add membership properly, should succeed
        self.login('david', 'david')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user2 is not requesting any more
        data = self.postAndParse('agora/1/membership_requests/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 0)

        # user2 is a member now
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 2)
        self.assertEquals(data['objects'][1]['username'], 'user2')

    def test_agora_add_membership2(self):
        '''
        Test that an admin can add a member
        '''

        # setting restricted joining policy
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'is_vote_secret': False,
                     'biography': "bio",
                     'membership_policy': 'JOINING_REQUIRES_ADMINS_APPROVAL',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # add user1, directly, without requesting membership
        orig_data = dict(action='add_membership', username='user1',
            welcome_message="weeEeEeelcome!")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user1 is a member now
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 2)
        self.assertEquals(data['objects'][1]['username'], 'user1')

    def test_agora_remove_membership(self):
        '''
        Test that an admin can remove a member
        '''

        # setting restricted joining policy
        self.login('david', 'david')
        orig_data = {'pretty_name': "updated name",
                     'short_description': "new desc",
                     'is_vote_secret': False,
                     'biography': "bio",
                     'membership_policy': 'JOINING_REQUIRES_ADMINS_APPROVAL',
                     'comments_policy': 'ANYONE_CAN_COMMENT'}
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # add user1
        orig_data = dict(action='add_membership', username='user1',
            welcome_message="weeEeEeelcome!")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user1 is a member now
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 2)
        self.assertEquals(data['objects'][1]['username'], 'user1')

        # trying to remove member with an user with no permissions,
        # should fail
        self.login('user1', '123')
        orig_data = dict(action='remove_membership', username='user1',
            goodbye_message="Goodbye!")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # user1 is still a member
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 2)
        self.assertEquals(data['objects'][1]['username'], 'user1')

        # removing membership
        self.login('david', 'david')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user1 is not a member anymore
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

        # removing membership from an user who is not a member
        orig_data = dict(action='remove_membership', username='user1',
            goodbye_message="Goodbye!")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

    def test_agora_leave(self):
        '''
        Test an user can leave the agora
        '''

        # user1 joins
        self.login('user1', '123')
        orig_data = dict(action="join")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user1 is a member now
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 2)
        self.assertEquals(data['objects'][1]['username'], 'user1')

        # leave
        orig_data = dict(action="leave")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # user1 is not a member anymore
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

        # leaving from an user who is not a member
        self.login('user2', '123')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # owner trying to leave
        self.login('david', 'david')
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # owner is still a member
        data = self.postAndParse('agora/1/members/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data['meta']['total_count'], 1)
        self.assertEquals(data['objects'][0]['username'], 'david')

    def test_agora_test_action(self):
        '''
        Basic tests on agora actions
        '''
        # method must be post so this fails
        data = self.get('agora/1/action/', code=HTTP_METHOD_NOT_ALLOWED)

        # no action provided so this fails
        data = self.post('agora/1/action/', data=dict(),
            code=HTTP_NOT_FOUND, content_type='application/json')

        # non existant action provided so this fails
        data = self.post('agora/1/action/', data=dict(action="3gt3g3gerr"),
            code=HTTP_NOT_FOUND, content_type='application/json')

        # test action correctly, so this succeeds
        orig_data = dict(action="test", param1="blah")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # now test action but with a inexistant agora, should fail
        data = self.post('agora/4454/action/', data=orig_data,
            code=HTTP_NOT_FOUND, content_type='application/json')

    def test_agora_get_perms(self):
        '''
        tests on agora get permissions
        '''
        orig_data = dict(action="get_permissions")

        # anonymous user has no special permissions
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data, dict(permissions=[]))

        # david user should have admin permissions
        self.login('david', 'david')
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data, dict(permissions=['admin', 'comment']))

        # user2 should have some permissions
        self.login('user2', '123')
        data = self.postAndParse('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')
        self.assertEquals(data, dict(permissions=['join', 'comment']))

    def test_send_request_membership_mails(self):
        '''
        test the celery send_request_membership_mails function
        '''
        kwargs=dict(
            agora_id=1,
            user_id=1,
            is_secure=True,
            site_id=Site.objects.all()[0].id,
            remote_addr='127.0.0.1'
        )
        result = send_request_membership_mails.apply_async(kwargs=kwargs)
        self.assertTrue(result.successful())

    def test_add_comment1(self):
        '''
        Tests adding a comment in the agora
        '''
        # get activity - its empty
        data = self.getAndParse('action/agora/1/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 0)

        # add a comment as anonymous - fails, forbidden
        orig_data = dict(comment='blah blah blah blah.')
        data = self.post('agora/1/add_comment/', orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # still no activity
        data = self.getAndParse('action/agora/1/')
        agoras = data['objects']
        self.assertEqual(len(agoras), 0)

        # add a comment as a logged in user that is a member of the agora
        self.login('david', 'david')
        data = self.postAndParse('agora/1/add_comment/', orig_data,
            code=HTTP_OK, content_type='application/json')

        # now the comment is there
        data = self.getAndParse('action/agora/1/')
        objects = data['objects']
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]['actor']['content_type'], 'user')
        self.assertEqual(objects[0]['actor']['username'], 'david')
        self.assertEqual(objects[0]['action_object']['content_type'], 'comment')
        self.assertEqual(objects[0]['action_object']['comment'], orig_data['comment'])

    def test_add_comment2(self):
        '''
        Tests adding a comment in the agora
        '''
        # no activity
        data = self.getAndParse('action/agora/1/')
        objects = data['objects']
        self.assertEqual(len(objects), 0)

        # set comment policy to only members
        self.login('david', 'david')
        orig_data = dict(comments_policy='ONLY_MEMBERS_CAN_COMMENT')
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # add a comment as a non member - fails
        self.login('user1', '123')
        orig_data = dict(comment='blah blah blah blah.')
        data = self.post('agora/1/add_comment/', orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # still no activity
        data = self.getAndParse('action/agora/1/')
        objects = data['objects']
        self.assertEqual(len(objects), 0)

        # user1 joins the agora
        orig_data = dict(action="join")
        data = self.post('agora/1/action/', data=orig_data,
            code=HTTP_OK, content_type='application/json')

        # this generates "joined" and "started following" actions
        data = self.getAndParse('action/agora/1/')
        objects = data['objects']
        self.assertEqual(len(objects), 2)

        # add a comment as a member - succeeds
        orig_data = dict(comment='blah blah blah blah 2 yeahh pirata.')
        data = self.post('agora/1/add_comment/', orig_data,
            code=HTTP_OK, content_type='application/json')

        # now the comment is there
        data = self.getAndParse('action/agora/1/')
        objects = data['objects']
        self.assertEqual(len(objects), 3)
        self.assertEqual(objects[0]['actor']['content_type'], 'user')
        self.assertEqual(objects[0]['actor']['username'], 'user1')
        self.assertEqual(objects[0]['action_object']['content_type'], 'comment')
        self.assertEqual(objects[0]['action_object']['comment'], orig_data['comment'])

    def test_add_comment3(self):
        '''
        Tests adding a comment in the agora
        '''
        # set comment policy to only admins
        self.login('david', 'david')
        orig_data = dict(comments_policy='ONLY_ADMINS_CAN_COMMENT')
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # try to post a comment as member - fails
        self.login('user1', '123')
        orig_data = dict(comment='blah blah blah blah 2 yeahh pirata.')
        data = self.post('agora/1/add_comment/', orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # the comment is not there
        data = self.getAndParse('action/agora/1/')
        objects = data['objects']
        self.assertEqual(len(objects), 0)

        # post the comment as agora admin
        self.login('david', 'david')
        orig_data = dict(comment='blah blah blah blah 2 yeahh pirata.')
        data = self.post('agora/1/add_comment/', orig_data,
            code=HTTP_OK, content_type='application/json')

        # now the comment is there
        data = self.getAndParse('action/agora/1/')
        objects = data['objects']
        self.assertEqual(len(objects), 1)

    def test_add_comment4(self):
        '''
        Tests adding a comment in the agora
        '''
        # set comment policy to no comments
        self.login('david', 'david')
        orig_data = dict(comments_policy='NO_COMMENTS')
        data = self.put('agora/1/', data=orig_data,
            code=HTTP_ACCEPTED, content_type='application/json')

        # post the comment as agora admin - fails, not even admins can post
        orig_data = dict(comment='blah blah blah blah 2 yeahh pirata.')
        data = self.post('agora/1/add_comment/', orig_data,
            code=HTTP_FORBIDDEN, content_type='application/json')

        # the comment is not there
        data = self.getAndParse('action/agora/1/')
        objects = data['objects']
        self.assertEqual(len(objects), 0)

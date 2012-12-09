from django.utils import unittest
from django.conf import settings

from agora import AgoraTest
from election import ElectionTest
from user import UserTest
from misc import MiscTest


# FIXME better url treatment
# FIXME relying on ordering when doing api set calls
# FIXME should construct data through posts


# This allows to test celery tasks
settings.CELERY_ALWAYS_EAGER = True
settings.BROKER_BACKEND = 'memory'

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(AgoraTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(ElectionTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(UserTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(MiscTest))
    return suite


from common import RootTestCase

# TODO
class CastVoteTest(RootTestCase):
    # TODO
    pass

class FollowTest(RootTestCase):
    # TODO
    pass

class ActionTest(RootTestCase):
    # TODO
    pass

from django.utils import unittest
from django.conf import settings

from agora import AgoraTest
from election import ElectionTest
from user import UserTest
from misc import MiscTest
from action import ActionTest
from search import SearchTest
from authority import AuthorityTest
from delegateelectioncount import DelegateElectionCountTest


# FIXME better url treatment
# FIXME relying on ordering when doing api set calls
# FIXME should construct data through posts


# This allows to test celery tasks
settings.CELERY_ALWAYS_EAGER = True
settings.BROKER_BACKEND = 'memory'
settings.AGORA_ALLOW_API_AUTO_ACTIVATION = True
settings.AGORA_API_AUTO_ACTIVATION_SECRET = 'change the activation secret'
settings.AGORA_CREATION_PERMISSIONS = "any-user"

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(AgoraTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(ElectionTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(UserTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(MiscTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(ActionTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(SearchTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(AuthorityTest))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(DelegateElectionCountTest))
    return suite


from common import RootTestCase

# TODO
class CastVoteTest(RootTestCase):
    # TODO
    pass

class FollowTest(RootTestCase):
    # TODO
    pass


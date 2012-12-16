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
    def test_nothing_at_all(self):
        pass
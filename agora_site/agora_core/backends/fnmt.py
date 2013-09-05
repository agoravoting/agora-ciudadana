# Copyright (C) 2013 Eduardo Robles Elvira <edulix AT wadobo DOT com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import random
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User

from userena.models import UserenaSignup

class FNMTBackend(object):
    """
    Authenticate against the settings ADMIN_LOGIN and ADMIN_PASSWORD.

    Use the login name, and a hash of the password. For example:

    ADMIN_LOGIN = 'admin'
    ADMIN_PASSWORD = 'sha1$4e987$afbcf42e21bd417fb71db8c66b321e9fc33051de'
    """

    def authenticate(self, cert_pem, full_name, email, nif):
        '''
        Register or logins the user and redirects it to the appropiate page
        '''
        self.cert_pem = cert_pem
        self.full_name = full_name
        self.email = email
        self.nif = nif
        user = User.objects.filter(email=self.email)

        # if we find an user with that email, login the user with that account,
        # setting NIF and full_name if needed
        if user.exists():
            user = user[0]
            profile = user.get_profile()
            modified = False
            if user.first_name != self.full_name:
                modified = True
                user.first_name = self.full_name
            if not isinstance(profile.extra, dict) or\
                    profile.extra.get("nif", '') != self.nif:
                modified = True
                if not isinstance(profile.extra, dict):
                    profile.extra = dict()
                profile.extra["nif"] = self.nif
            if not isinstance(profile.extra, dict) or\
                    profile.extra.get("fnmt_cert", '') != self.cert_pem:
                modified = True
                if not isinstance(profile.extra, dict):
                    profile.extra = dict()
                profile.extra["fnmt_cert"] = self.cert_pem

            if not user.is_active:
                user.is_active = True
                modified = True

            if modified:
                user.save()
                profile.save()
            return user

        user = User.objects.filter(first_name=self.full_name)
        if user.exists():
            user = user[0]
            modified = False
            profile = user.get_profile()

            # only if there's an user with different email but same full name
            # and nif authenticate with it
            if isinstance(profile.extra, dict) and\
                    profile.extra.get('nif', '') == self.nif:
                if not user.is_active:
                    user.is_active = True
                    modified = True
                if not isinstance(profile.extra, dict) or\
                        profile.extra.get("fnmt_cert", '') != self.fnmt_cert:
                    modified = True
                    if not isinstance(profile.extra, dict):
                        profile.extra = dict()
                    profile.extra["fnmt_cert"] = self.cert_pem
                if modified:
                    user.save()
                    profile.save()
                return user

        # in all other cases, we need to register this as a new user

        # generate a valid new username
        base_username = username = self.email.split('@')[0]
        while User.objects.filter(username=username).exists():
            username = base_username + random.randint(0, 100)

        # generate a new password (just because it's needed - user will only
        # login using the fnmt login method by default)
        password =str(uuid4())
        new_user = UserenaSignup.objects.create_user(username, self.email,
            password, True, False)
        new_user.first_name = self.full_name
        new_user.save()

        profile = new_user.get_profile()
        profile.extra = dict(nif=self.nif, fnmt_cert=self.cert_pem)
        profile.save()

        return new_user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
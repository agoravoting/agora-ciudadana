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
from django.template.defaultfilters import slugify

from userena.models import UserenaSignup

class FNMTBackend(object):
    """
    Authenticate using the fnmt certificate.
    """

    def authenticate(self, cert_pem, full_name, email, nif):
        '''
        Register or logins the user and redirects it to the appropiate page
        '''
        self.cert_pem = cert_pem
        self.full_name = full_name
        self.email = email
        self.nif = nif
        if email is not None:
            user = User.objects.filter(email=self.email)

        # if we find an user with that email, login the user with that account,
        # setting NIF and full_name if needed
        if email and user.exists():
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
                if not isinstance(profile.extra, dict) or\
                        profile.extra.get("fnmt_cert", '') != self.cert_pem:
                    modified = True
                    if not isinstance(profile.extra, dict):
                        profile.extra = dict()
                    profile.extra["fnmt_cert"] = self.cert_pem
                if modified:
                    user.save()
                    profile.save()
                return user

        # in all other cases, we need to register this as a new user

        activate_user = email is not None

        if email is not None:
            # generate a valid new username
            base_username = username = slugify(self.email.split('@')[0])
            while User.objects.filter(username=username).exists():
                username = base_username + str(random.randint(0, 100))
        else:
            base_username = "user"
            username = base_username + str(uuid4())[:6]
            while User.objects.filter(username=username).exists():
                username = base_username + str(uuid4())[:6]
            email = "%s@example.com" % str(uuid4())


        # generate a new password (just because it's needed - user will only
        # login using the fnmt login method by default)
        password = str(uuid4())
        new_user = UserenaSignup.objects.create_user(username, self.email,
            password, activate_user, False)
        new_user.first_name = self.full_name
        new_user.password = '!'
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

def fnmt_data_from_pem(pem):
    '''
    given an FNMT PEM certificate, returns the relevant data from it:
    returns nif, full_name, email

    The certificate might not contain an email - in that case it will return
    None for the email.

    If there's any error processing the certificate, it will throw an exception
    '''

    import OpenSSL
    from pyasn1.type.base import AbstractConstructedAsn1Item
    from pyasn1.type.char import IA5String
    from pyasn1.codec.der.decoder import decode
    from pyasn1_modules.rfc2459 import SubjectAltName, AttributeTypeAndValue, GeneralName

    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pem)

    # sanity check
    components = cert.get_subject().get_components()
    assert components[0][0].lower() == 'c'
    assert components[0][1].lower() == 'es'

    assert components[1][0].lower() == 'o'
    assert components[1][1].lower() == 'fnmt'

    assert components[2][0].lower() == 'ou'
    assert components[2][1].lower() == 'fnmt clase 2 ca'

    assert components[4][0].lower() == 'cn'

    def visit_asn(data, item):
        '''
        visits asn items locating and saving relevant data
        '''
        if isinstance(item, IA5String):
            data['email'] = str(item).lower()
        elif isinstance(item, AttributeTypeAndValue):
            item_type = str(item[0])
            if item_type == '1.3.6.1.4.1.5734.1.1':
                data['name'] = decode(item[1])[0].asOctets().decode('latin-1', 'ignore')
            elif item_type == '1.3.6.1.4.1.5734.1.2':
                data['surname1'] = decode(item[1])[0].asOctets().decode('latin-1', 'ignore')
            elif item_type == '1.3.6.1.4.1.5734.1.3':
                data['surname2'] = decode(item[1])[0].asOctets().decode('latin-1', 'ignore')
            elif item_type == '1.3.6.1.4.1.5734.1.4':
                data['nif'] = decode(item[1])[0].asOctets().decode('latin-1', 'ignore')
        elif isinstance(item, AbstractConstructedAsn1Item) or isinstance(item, tuple):
            for child_item in item:
                visit_asn(data, child_item)

    # find subjectAltName, which should contain user's email address
    for i in xrange(cert.get_extension_count()):
        ext = cert.get_extension(i)
        if ext.get_short_name() == 'subjectAltName':
            alt_name = decode(ext.get_data(), asn1Spec=SubjectAltName())

            data = dict()
            visit_asn(data, alt_name)

            # check that everything was found
            assert data.has_key('nif')
            assert data.has_key('surname1')
            assert data.has_key('name')
            # email and surname2 might not be found

            # as strange as it might sound, there are some people that actually
            # do not have a second surname, so we don't assert on that and take
            # that case into account
            if data.has_key('surname2'):
                full_name = u"%s %s %s" % (data['name'], data['surname1'], data['surname2'])
            else:
                full_name = u"%s %s" % (data['name'], data['surname1'])
            full_name = u" ".join([i.capitalize() for i in full_name.split(" ")])
            full_name = full_name[:140]

            return data['nif'], full_name, data.get('email', None)

    raise Exception("subjectAltName not found in the certificate")

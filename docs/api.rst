=======
API
=======

Agora ciudadana exports a REST API with full access to the data model and user actions.

Format
======

Access to /api/v1/xxxx to use the API resources, using the corresponding HTTP methods (GET, POST, PUT, DELETE...).

Requests and answers may use any of the standard formats: xml, json or yaml. The format may be specified via "Accept"
HTTP headers or with ?format=json (or xml or yaml) parameter in the URL.

API calls use the standard HTTP codes for status reporting (200 OK, 404 Not Found, 403 Forbidden, etc.). In case of
error, the returned data may have fields with additional info (see each individual call for more explanations).


Authentication
==============

The API accepts two modes of authentication:

**Session authentication**

The session cookie used in the normal login is accepted and identifies the user that is using the API. This is useful
mainly for the javascript embedded in the own Agora pages.

**Token authentication**

For access the API with an external application, you need the auth token. When you call the login API function, the
user token is returned, and you must supply it in the Authorization header in all next HTTP calls:

.. code-block:: http

    # As a header
    # Format is ''Authorization: ApiKey <username>:<api_key>''
    Authorization: ApiKey daniel:204db7bcfafb2deb7506b89eb3b9b715b09905c8

**Status reporting**

API calls use the standard HTTP codes for status reporting (200 OK, 404 Not Found, 403 Forbidden, etc.). In case of
error, the returned data may have fields with additional info (see each individual call for more explanations).

Lists, Pagination and filtering
===============================

When a list of resources is needed, Agora API always paginates the results. One can set a specific offset and limit the number of items. Also some listings allow filtering by some fields, for example a list of users might filter by username.

Filter fields sometimes are said to support django field lookups. In this case if this happens when filtering by username, you can also do a more advanced filtering by filtering only usernames that start with a given string with `username__startswith` parameter. See the different django field lookups available in https://docs.djangoproject.com/en/dev/ref/models/querysets/

Resource: Agora
===============

.. http:get:: /agora/

   List agoras

   :query offset: offset number. default is 0
   :query limit: limit number. default is 20
   :query name: filter by `name` of the agora. It allows all django filter types.
   :statuscode 200 OK: no error

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
       "meta":
       {
           "limit": 20,
           "next": null,
           "offset": 0,
           "previous": null,
           "total_count": 4
       },
       "objects":
       [
           {
               "archived_at_date": null,
               "biography": "",
               "comments_policy": "aaaaaaa",
               "created_at_date": "2012-12-16T18:10:25.583006",
               "creator":
               {
                   "date_joined": "2012-06-16T17:04:15.016445",
                   "first_name": "edulix",
                   "id": 2,
                   "is_active": true,
                   "last_login": "2012-12-16T18:08:04.271163",
                   "last_name": "Robles Elvira",
                   "username": "edulix"
               },
               "election_type": "ONCE_CHOICE",
               "eligibility": "",
               "extra_data": "",
               "id": 2,
               "image_url": "",
               "is_vote_secret": false,
               "membership_policy": "ANYONE_CAN_JOIN",
               "name": "blahblah",
               "pretty_name": " blahblah",
               "short_description": "blahblah"
           },
           {
               "archived_at_date": null,
               "biography": "",
               "comments_policy": "ANYONE_CAN_COMMENT",
               "created_at_date": "2012-10-10T01:15:04.603246",
               "creator":
               {
                   "date_joined": "2012-09-05T17:45:40.223602",
                   "first_name": "Juana Molero",
                   "id": 12,
                   "is_active": true,
                   "last_login": "2012-10-10T00:06:47.741392",
                   "last_name": "",
                   "username": "user10"
               },
               "election_type": "ONCE_CHOICE",
               "eligibility": "",
               "extra_data": "",
               "id": 3,
               "image_url": "",
               "is_vote_secret": true,
               "membership_policy": "JOINING_REQUIRES_ADMINS_APPROVAL",
               "name": "testagora",
               "pretty_name": "testagora",
               "short_description": "yeahhhhhh"
           },
           {
               "archived_at_date": null,
               "biography": "",
               "comments_policy": "ONLY_MEMBERS_CAN_COMMENT",
               "created_at_date": "2012-12-13T14:12:03.711985",
               "creator":
               {
                   "date_joined": "2012-09-05T17:45:48.390074",
                   "first_name": "Victoria Ariza",
                   "id": 22,
                   "is_active": true,
                   "last_login": "2012-12-18T10:35:07.444961",
                   "last_name": "",
                   "username": "user20"
               },
               "election_type": "ONCE_CHOICE",
               "eligibility": "",
               "extra_data": "",
               "id": 4,
               "image_url": "",
               "is_vote_secret": false,
               "membership_policy": "JOINING_REQUIRES_ADMINS_APPROVAL",
               "name": "testagora",
               "pretty_name": "testagora",
               "short_description": "tesagora yeah"
           },
           {
               "archived_at_date": null,
               "biography": "",
               "comments_policy": "ANYONE_CAN_COMMENT",
               "created_at_date": "2012-12-02T16:35:52.110729",
               "creator":
               {
                   "date_joined": "2012-06-14T14:13:48.850044",
                   "first_name": "",
                   "id": 1,
                   "is_active": true,
                   "last_login": "2012-12-16T18:06:25.185835",
                   "last_name": "",
                   "username": "admin"
               },
               "election_type": "ONCE_CHOICE",
               "eligibility": "",
               "extra_data": "",
               "id": 5,
               "image_url": "",
               "is_vote_secret": false,
               "membership_policy": "ANYONE_CAN_JOIN",
               "name": "created-agora",
               "pretty_name": "created agora",
               "short_description": "created agora description"
           }
       ]
    }

.. http:get:: /agora/(int:agora_id)

   Retrieves an agora (`agora_id`).

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: when agora is retrieved correctly
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/5/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "archived_at_date": null,
        "biography": "",
        "comments_policy": "ANYONE_CAN_COMMENT",
        "created_at_date": "2012-12-02T16:35:52.110729",
        "creator":
        {
            "date_joined": "2012-06-14T14:13:48.850044",
            "first_name": "",
            "id": 1,
            "is_active": true,
            "last_login": "2012-12-16T18:06:25.185835",
            "last_name": "",
            "username": "admin"
        },
        "election_type": "ONCE_CHOICE",
        "eligibility": "",
        "extra_data": "",
        "id": 5,
        "image_url": "",
        "is_vote_secret": true,
        "membership_policy": "ANYONE_CAN_JOIN",
        "name": "agora-name",
        "pretty_name": "agora name",
        "short_description": "some fancydescription"
    }

.. http:post:: /agora/

   Create a new agora. Requires agora creation permissions.

   Agora creation permissions are specified in ``settings.py`` with the
   ``AGORA_CREATION_PERMISSIONS`` setting. By default it's set to ``any-user``
   which means any authenticated user can create a new agora. But it can also
   be set to ``superusers-only`` which means only site admins can create new
   agoras.

   :form pretty_name: readable agora name. Required.
   :form short_description: short description text. Required.
   :form is_vote_secret: whether the vote is secret in this agora. Optional. False by default.
   :status 201 CREATED: when agora is created correctly
   :status 403 FORBIDDEN: when the user has no agora creation permissions
   :status 400 BAD REQUEST: when the form parameters are invalid

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/agora/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

    {
        "pretty_name": "agora name",
        "short_description": "some fancydescription",
        "is_vote_secret": true
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 201 CREATED
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "archived_at_date": null,
        "biography": "",
        "comments_policy": "ANYONE_CAN_COMMENT",
        "created_at_date": "2012-12-02T16:35:52.110729",
        "creator":
        {
            "date_joined": "2012-06-14T14:13:48.850044",
            "first_name": "",
            "id": 1,
            "is_active": true,
            "last_login": "2012-12-16T18:06:25.185835",
            "last_name": "",
            "username": "admin"
        },
        "election_type": "ONCE_CHOICE",
        "eligibility": "",
        "extra_data": "",
        "id": 5,
        "image_url": "",
        "is_vote_secret": true,
        "membership_policy": "ANYONE_CAN_JOIN",
        "name": "agora-name",
        "pretty_name": "agora name",
        "short_description": "some fancydescription"
    }

.. http:delete:: /agora/(int:agora_id)

   Deletes the agora (`agora_id`). Requires to be authentication with the user
   that created that agora.

   :param agora_id: agora's unique id
   :type agora_id: int
   :statuscode 204 HTTP_NO_CONTENT: agora was deleted
   :status 403 FORBIDDEN: when the user has no agora delete permissions

   **Example request**:

   .. sourcecode:: http

    DELETE /api/v1/agora/39/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 204 NO CONTENT
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8


.. http:put:: /agora/

   Modifies an agora (`agora_id`). Requires the authenticated user to be an
   administrator of the agora.

   :form pretty_name: readable agora name. Required.
   :form short_description: short description text. Required.
   :form is_vote_secret: whether the vote is secret in this agora. Optional. False by default.
   :form biography: longer description text. Optional. Empty by default.
   :form membership_policy: membership policy. Optional. Possible values are: ``ANYONE_CAN_JOIN``, ``JOINING_REQUIRES_ADMINS_APPROVAL_ANY_DELEGATE``, ``JOINING_REQUIRES_ADMINS_APPROVAL``. ``ANYONE_CAN_JOIN`` by default.
   :form comments_policy: comments policy. Optional. Possible values are: ``ANYONE_CAN_COMMENT``, ``ONLY_MEMBERS_CAN_COMMENT``, ``ONLY_ADMINS_CAN_COMMENT``, ``NO_COMMENTS``. ``ANYONE_CAN_COMMENT`` by default.
   :status 202 CREATED: when agora is modified correctly
   :status 403 FORBIDDEN: when the user has no agora administration permissions
   :status 400 BAD REQUEST: when the form parameters are invalid

   .. sourcecode:: http

    PUT /api/v1/agora/5/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

    {
        "pretty_name": "agora name",
        "short_description": "some fancydescription",
        "is_vote_secret": true,
        "comments_policy": "ANYONE_CAN_COMMENT",
        "membership_policy": "ANYONE_CAN_JOIN",
        "biography": "",
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 202 ACCEPTED
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "archived_at_date": null,
        "biography": "",
        "comments_policy": "ANYONE_CAN_COMMENT",
        "created_at_date": "2012-12-02T16:35:52.110729",
        "creator":
        {
            "date_joined": "2012-06-14T14:13:48.850044",
            "first_name": "",
            "id": 1,
            "is_active": true,
            "last_login": "2012-12-16T18:06:25.185835",
            "last_name": "",
            "username": "admin"
        },
        "election_type": "ONCE_CHOICE",
        "eligibility": "",
        "extra_data": "",
        "id": 5,
        "image_url": "",
        "is_vote_secret": true,
        "membership_policy": "ANYONE_CAN_JOIN",
        "name": "agora-name",
        "pretty_name": "agora name",
        "short_description": "some fancydescription"
    }


Resource: User
==============

.. http:get:: /user/

   List users

   :query offset: offset number. default is 0
   :query limit: limit number. default is 20
   :statuscode 200 OK: no error

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/user/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
       "meta":
       {
           "limit": 20,
           "next": null,
           "offset": 0,
           "previous": null,
           "total_count": 3
       },
       "objects":
       [
           {
               "date_joined": "2012-06-14T14:13:48.850044",
               "first_name": "",
               "id": 1,
               "is_active": true,
               "last_login": "2012-12-16T18:06:25.185835",
               "last_name": "",
               "username": "admin"
           },
           {
               "date_joined": "2012-06-16T17:04:15.016445",
               "first_name": "edulix",
               "id": 2,
               "is_active": true,
               "last_login": "2012-12-16T18:08:04.271163",
               "last_name": "Robles Elvira",
               "username": "edulix"
           },
           {
               "date_joined": "2012-09-05T17:45:32.215085",
               "first_name": "Maria Robles",
               "id": 3,
               "is_active": true,
               "last_login": "2012-10-07T15:38:16.076439",
               "last_name": "",
               "username": "user1"
           }
       ]
    }

.. http:get:: /user/settings/

   Shows authenticated user information

   :statuscode 200 OK: no error

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/user/settings/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "date_joined": "2012-11-29T15:07:55.727000",
        "first_name": "David",
        "id": 0,
        "is_active": true,
        "last_login": "2012-11-29T15:07:55.727000",
        "last_name": "",
        "username": "david"
    }

.. http:post:: /user/register/

   Registers a new user.

   :form email: New user email address. Required.
   :form password1: New user password. Required.
   :form password2: New user password again. It must be equal to passwors1. Required.
   :form username: The new user identifier, It should be unique in the application. Required.
   :status 200 OK: when the user is registered correctly
   :status 400 BAD REQUEST: when the form parameters are invalid

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/user/register/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

    {
        "username": "danigm",
        "password1": "my super secret password",
        "password2": "my super secret password",
        "email": "danigm@wadobo.com"
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

.. http:post:: /user/login/

   Login in the application.

   :form identification: The user username to login. Required.
   :form password: The user password. Required.
   :status 200 OK: when the user is loged in correctly
   :status 400 BAD REQUEST: when the form parameters are invalid

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/user/login/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

    {
        "identification": "danigm",
        "password": "my super secret password"
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

.. http:post:: /user/logout/

   Logout in the application.

   :status 200 OK: when the user is loged in correctly

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/user/logout/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

.. http:get:: /user/username_available/

   Checks if a username is avaliable

   :status 200 OK: when the username is available
   :status 400 BAD REQUEST: when the username isn't available

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/user/username_available/?username=danigm HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8


Resource: Election
==================

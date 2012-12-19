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

List Agoras
-----------

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

Retrieve an agora
-----------------

.. http:get:: /agora/(int:agora_id)

   Retrieves an agora (`agora_id`).

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
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

Create a new agora
------------------

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

Delete an agora
---------------

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

Modify agora
------------

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

Retrieve agora members
----------------------

.. http:get:: /agora/(int:agora_id)/members

   Retrieves all the users that are members of agora (`agora_id`).

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/members/ HTTP/1.1
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
           "offset": 0,
           "total_count": 2
       },
       "objects":
       [
           {
               "date_joined": "2012-12-18T15:46:35.590347",
               "first_name": "Isabel Romero",
               "id": 2,
               "is_active": true,
               "last_login": "2012-12-18T15:47:35.109371",
               "last_name": "",
               "username": "user1"
           },
           {
               "date_joined": "2012-12-18T15:46:37.644236",
               "first_name": "Maria Moreno",
               "id": 5,
               "is_active": true,
               "last_login": "2012-12-18T15:55:12.833627",
               "last_name": "",
               "username": "user4"
           }
       ]
    }

Retrieve agora administrators
-----------------------------

.. http:get:: /agora/(int:agora_id)/admins

   Retrieves the users that are admin members of agora (`agora_id`).

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/admins/ HTTP/1.1
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
           "offset": 0,
           "total_count": 1
       },
       "objects":
       [
           {
               "date_joined": "2012-12-18T15:46:35.590347",
               "first_name": "Isabel Romero",
               "id": 2,
               "is_active": true,
               "last_login": "2012-12-18T15:47:35.109371",
               "last_name": "",
               "username": "user1"
           }
       ]
    }

Retrieve agora membership requests
----------------------------------

.. http:get:: /agora/(int:agora_id)/membership_requests

   Retrieves the users that have pending requests to become members of agora (`agora_id`).

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/membership_requests/ HTTP/1.1
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
           "offset": 0,
           "total_count": 1
       },
       "objects":
       [
           {
               "date_joined": "2012-12-18T15:46:38.968369",
               "first_name": "Monica Moreno",
               "id": 7,
               "is_active": true,
               "last_login": "2012-12-18T16:31:32.390732",
               "last_name": "",
               "username": "user6"
           }
       ]
    }

Retrieve agora active delegates
-------------------------------

.. http:get:: /agora/(int:agora_id)/active_delegates

   Retrieves active delegates of agora (`agora_id`): users that have emitted any valid
   and public vote in any election of this agora.

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/active_delegates/ HTTP/1.1
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
           "offset": 0,
           "total_count": 1
       },
       "objects":
       [
           {
               "date_joined": "2012-12-18T15:46:37.041147",
               "first_name": "Juana Garcia",
               "id": 4,
               "is_active": true,
               "last_login": "2012-12-18T15:46:37.041112",
               "last_name": "",
               "username": "user3"
           }
       ]
    }

Retrieve all agora elections
----------------------------

.. http:get:: /agora/(int:agora_id)/all_elections

   Retrieves all elections in agora (`agora_id`).

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/all_elections/ HTTP/1.1
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
           "offset": 0,
           "total_count": 1
       },
       "objects":
       [
           {
               "agora": "/api/v1/agora/1/",
               "approved_at_date": null,
               "archived_at_date": null,
               "comments_policy": "ANYONE_CAN_COMMENT",
               "created_at_date": "2012-12-18T15:53:05.265843",
               "creator": "/api/v1/user/2/",
               "delegated_votes_frozen_at_date": null,
               "delegated_votes_result": "",
               "description": "this is election 2",
               "election_type": "ONE_CHOICE",
               "electorate":
               [
               ],
               "eligibility": "",
               "extra_data": "{u'started': True}",
               "frozen_at_date": "2012-12-18T15:53:24.071076",
               "hash": "b05bc33717cacc1557ff47bffdbfecbf10d3a1a52baba603b5b7b8e10c6db9fa",
               "id": 4,
               "is_approved": true,
               "is_vote_secret": false,
               "last_modified_at_date": "2012-12-18T15:53:05.275983",
               "name": "election-2",
               "parent_election": null,
               "percentage_of_participation": 50,
               "pretty_name": "election 2",
               "questions": "[{u'a': u'ballot/question', u'min': 0, u'max': 1, u'tally_type': u'simple', u'question': u'question of election 2', u'answers': [{u'a': u'ballot/answer', u'url': u'', u'details': u'', u'value': u'yes'}, {u'a': u'ballot/answer', u'url': u'', u'details': u'', u'value': u'no'}], u'randomize_answer_order': True}]",
               "resource_uri": "/api/v1/election/4/",
               "result": "",
               "result_tallied_at_date": null,
               "short_description": "this is election 2",
               "tiny_hash": null,
               "url": "http://localhost:8000/user1/agora1/election/election-2",
               "uuid": "318707f0-fd82-4d1a-b70a-9ee25c77000b",
               "voters_frozen_at_date": null,
               "voting_ends_at_date": null,
               "voting_extended_until_date": null,
               "voting_starts_at_date": "2012-12-18T15:58:12.728550"
           }
       ]
    }

Retrieve tallied agora elections
--------------------------------

.. http:get:: /agora/(int:agora_id)/tallied_elections

   Retrieves tallied elections in agora (`agora_id`): past elections that are
   closed and with a result.

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/tallied_elections/ HTTP/1.1
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
           "offset": 0,
           "total_count": 1
       },
       "objects":
       [
           {
               "agora": "/api/v1/agora/2/",
               "approved_at_date": null,
               "archived_at_date": null,
               "comments_policy": "ANYONE_CAN_COMMENT",
               "created_at_date": "2012-12-18T15:54:17.742549",
               "creator": "/api/v1/user/2/",
               "delegated_votes_frozen_at_date": "2012-12-18T17:15:40.772925",
               "delegated_votes_result": "{u'delegation_counts': [], u'a': u'result', u'election_counts': [[0, 0, 0]]}",
               "description": "this is election 3",
               "election_type": "ONE_CHOICE",
               "electorate":
               [
                   "/api/v1/user/2/",
                   "/api/v1/user/5/"
               ],
               "eligibility": "",
               "extra_data": "{u'started': True, u'ended': True}",
               "frozen_at_date": "2012-12-18T15:54:22.296002",
               "hash": "e707a91d4657e9f0c2dabeb72c6c4598b468159b409844f87160457aa9de1dc4",
               "id": 5,
               "is_approved": true,
               "is_vote_secret": false,
               "last_modified_at_date": "2012-12-18T15:54:17.758384",
               "name": "election-3",
               "parent_election": null,
               "percentage_of_participation": 100,
               "pretty_name": "election 3",
               "questions": "[{u'a': u'ballot/question', u'min': 0, u'max': 1, u'tally_type': u'simple', u'question': u'question of election 3', u'answers': [{u'a': u'ballot/answer', u'by_delegation_count': 0, u'url': u'', u'by_direct_vote_count': 0, u'value': u'a', u'details': u''}, {u'a': u'ballot/answer', u'by_delegation_count': 0, u'url': u'', u'by_direct_vote_count': 1, u'value': u'b', u'details': u''}, {u'a': u'ballot/answer', u'by_delegation_count': 0, u'url': u'', u'by_direct_vote_count': 1, u'value': u'c', u'details': u''}], u'randomize_answer_order': True}]",
               "resource_uri": "/api/v1/election/5/",
               "result": "[{u'a': u'ballot/question', u'min': 0, u'max': 1, u'tally_type': u'simple', u'question': u'question of election 3', u'answers': [{u'a': u'ballot/answer', u'by_delegation_count': 0, u'url': u'', u'by_direct_vote_count': 0, u'value': u'a', u'details': u''}, {u'a': u'ballot/answer', u'by_delegation_count': 0, u'url': u'', u'by_direct_vote_count': 1, u'value': u'b', u'details': u''}, {u'a': u'ballot/answer', u'by_delegation_count': 0, u'url': u'', u'by_direct_vote_count': 1, u'value': u'c', u'details': u''}], u'randomize_answer_order': True}]",
               "result_tallied_at_date": "2012-12-18T17:15:40.772925",
               "short_description": "this is election 3",
               "tiny_hash": null,
               "url": "http://localhost:8000/user1/agora2/election/election-3",
               "uuid": "9dffc9c2-a2a2-4837-a8c5-3e20cb06f965",
               "voters_frozen_at_date": "2012-12-18T17:15:40.772925",
               "voting_ends_at_date": "2012-12-18T17:15:40.188654",
               "voting_extended_until_date": "2012-12-18T17:15:40.434542",
               "voting_starts_at_date": "2012-12-18T15:54:28.043188"
           }
       ]
    }

Retrieve open agora elections
--------------------------------

.. http:get:: /agora/(int:agora_id)/open_elections

   Retrieves tallied elections in agora (`agora_id`): current or future elections that
   will or are taking place in the agora.

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/open_elections/ HTTP/1.1
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
           "offset": 0,
           "total_count": 1
       },
       "objects":
       [
           {
               "agora": "/api/v1/agora/2/",
               "approved_at_date": null,
               "archived_at_date": null,
               "comments_policy": "ANYONE_CAN_COMMENT",
               "created_at_date": "2012-12-18T15:50:48.576146",
               "creator": "/api/v1/user/2/",
               "delegated_votes_frozen_at_date": null,
               "delegated_votes_result": "",
               "description": "this is election 1",
               "election_type": "ONE_CHOICE",
               "electorate":
               [
               ],
               "eligibility": "",
               "extra_data": "{u'started': True}",
               "frozen_at_date": "2012-12-18T15:51:05.405218",
               "hash": "4e7b9fd6e8fa6e35182743ee19a4102ba3b996b38497660be4d173095ad45b91",
               "id": 3,
               "is_approved": true,
               "is_vote_secret": true,
               "last_modified_at_date": "2012-12-18T15:50:48.588385",
               "name": "election-1",
               "parent_election": null,
               "percentage_of_participation": 50,
               "pretty_name": "election 1",
               "questions": "[{u'a': u'ballot/question', u'tally_type': u'simple', u'max': 1, u'min': 0, u'question': u'question of election 1', u'answers': [{u'a': u'ballot/answer', u'url': u'', u'details': u'', u'value': u'one'}, {u'a': u'ballot/answer', u'url': u'', u'details': u'', u'value': u'two'}, {u'a': u'ballot/answer', u'url': u'', u'details': u'', u'value': u'three'}], u'randomize_answer_order': True}]",
               "resource_uri": "/api/v1/election/3/",
               "result": "",
               "result_tallied_at_date": null,
               "short_description": "this is election 1",
               "tiny_hash": null,
               "url": "http://localhost:8000/user1/agora2/election/election-1",
               "uuid": "c2ad36c2-b67e-499c-8100-59becd538549",
               "voters_frozen_at_date": null,
               "voting_ends_at_date": "2012-12-20T00:00:00",
               "voting_extended_until_date": "2012-12-20T00:00:00",
               "voting_starts_at_date": "2012-12-18T16:51:00.018431"
           }
       ]
    }



Resource: User
==============

List users
----------

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

User settings
-------------

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

User register
-------------

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

User login
----------

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

User logout
-----------

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

Check username is available
---------------------------

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

List current user agoras
------------------------

.. http:get:: /user/agoras/

   List authenticated user's agoras. Requires an user to be authenticated.

   :query offset: offset number. default is 0
   :query limit: limit number. default is 20
   :statuscode 200 OK: no error
   :statuscode 403 FORBIDDEN: when the user is not authenticated

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/user/agoras/ HTTP/1.1
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
           "offset": 0,
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

List elections this user can vote in
------------------------------------

.. http:get:: /user/open_elections/

   List elections the authenticated  user can vote in. These are the elections
   that are open in the agoras in which this user is a member. Requires an user
   to be authenticated.

   :query offset: offset number. default is 0
   :query limit: limit number. default is 20
   :query q: search string, not required. filters in the election name and description
   :statuscode 200 OK: no error
   :statuscode 403 FORBIDDEN: when the user is not authenticated

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/user/open_elections/?q=vota HTTP/1.1
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
           "offset": 0,
           "total_count": 1
       },
       "objects":
       [
           {
               "agora": "/api/v1/agora/4/",
               "approved_at_date": null,
               "archived_at_date": null,
               "comments_policy": "ANYONE_CAN_COMMENT",
               "created_at_date": "2012-10-28T09:36:30.951957",
               "creator": "/api/v1/user/22/",
               "delegated_votes_frozen_at_date": null,
               "delegated_votes_result": "",
               "description": "blah",
               "election_type": "ONCE_CHOICE",
               "electorate":
               [
               ],
               "eligibility": "",
               "extra_data": "{u'started': True}",
               "frozen_at_date": "2012-10-28T09:36:44.106801",
               "has_user_voted": true,
               "has_user_voted_via_a_delegate": false,
               "hash": "057e6e4a31ca99089ae5d5826723f29e6ee119f9a4f9066a560c5e39e9f58500",
               "id": 27,
               "is_approved": true,
               "is_vote_secret": true,
               "last_modified_at_date": "2012-10-28T09:36:30.962801",
               "name": "votacion-de-prueba",
               "parent_election": null,
               "percentage_of_participation": 22.22222222222222,
               "pretty_name": "Votación de prueba",
               "questions": "[{u'a': u'ballot/question', u'tally_type': u'simple', u'max': 1, u'min': 0, u'question': u'\xbfEs molona la votaci\xf3n?', u'answers': [{u'a': u'ballot/answer', u'url': u'', u'details': u'', u'value': u'S\xed'}, {u'a': u'ballot/answer', u'url': u'', u'details': u'', u'value': u'No'}], u'randomize_answer_order': True}]",
               "resource_uri": "",
               "result": "",
               "result_tallied_at_date": null,
               "short_description": "blah",
               "tiny_hash": null,
               "url": "http://local.dev:8000/user20/testagora/election/votacion-de-prueba",
               "uuid": "3c4b6bbc-24ca-4d82-832e-27e049d9cc85",
               "voters_frozen_at_date": null,
               "voting_ends_at_date": null,
               "voting_extended_until_date": null,
               "voting_starts_at_date": "2012-11-03T08:39:49.019238"
           }
       ]
    }




Resource: Search
================

This resource allows searches, using Haystack


.. http:get:: /search/

   Searches objects using haystack. It can return agoras, elections and profiles.

   :query offset: offset number. default is 0
   :query limit: limit number. default is 20
   :query q: search string, not required
   :statuscode 200 OK: no error

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/search/?q=vota HTTP/1.1
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
           "total_count": 8
       },
       "objects":
       [
           {
               "obj":
               {
                   "content_type": "profile",
                   "first_name": "edulix",
                   "id": 3,
                   "url": "/user/edulix",
                   "user_id": 2,
                   "username": "edulix"
               }
           },
           {
               "obj":
               {
                   "content_type": "election",
                   "id": 23,
                   "name": "me-aprobara-rock-neurotico-esta-votacion",
                   "pretty_name": "¿Me aprobará rock neurótico ésta votación?",
                   "short_description": "aaaaaa",
                   "url": "/edulix/blahblah/election/me-aprobara-rock-neurotico-esta-votacion"
               }
           },
           {
               "obj":
               {
                   "content_type": "profile",
                   "first_name": "",
                   "id": 1,
                   "url": "/user/admin",
                   "user_id": 1,
                   "username": "admin"
               }
           },
           {
               "obj":
               {
                   "content_type": "agora",
                   "id": 2,
                   "name": "blahblah",
                   "pretty_name": " blahblah",
                   "short_description": "blahblah",
                   "url": "/edulix/blahblah"
               }
           },
           {
               "obj":
               {
                   "content_type": "profile",
                   "first_name": "probando1",
                   "id": 55,
                   "url": "/user/probando1",
                   "user_id": 54,
                   "username": "probando1"
               }
           },
           {
               "obj":
               {
                   "content_type": "profile",
                   "first_name": "probando2",
                   "id": 56,
                   "url": "/user/probando2",
                   "user_id": 55,
                   "username": "probando2"
               }
           },
           {
               "obj":
               {
                   "content_type": "profile",
                   "first_name": "probando3",
                   "id": 57,
                   "url": "/user/probando3",
                   "user_id": 56,
                   "username": "probando3"
               }
           },
           {
               "obj":
               {
                   "content_type": "election",
                   "id": 4,
                   "name": "delegation",
                   "pretty_name": "",
                   "short_description": "voting used for delegation",
                   "url": "/edulix/blahblah/election/delegation"
               }
           }
       ]
    }




=======
API
=======

Agora ciudadana exports a REST API with full access to the data model and user actions.

Format
======

Access to /api/v1/xxxx to use the API resources, using the corresponding HTTP methods (GET, POST, PUT, DELETE...).

Requests and answers may use any of the standard formats: xml, json or yaml. The format may be specified via "Accept"
HTTP headers or with ?format=json (or xml or yaml) parameter in the URL.

**Status reporting**

API calls use the standard HTTP codes for status reporting (200 OK, 404 Not Found, 403 Forbidden, etc.). In case of
error, the returned data may have fields with additional info (see each individual call for more explanations).


Authentication
==============

The API accepts two modes of authentication:

**Readonly unathenticated queries**

Some read-only queries can be requested with no authentication mechanism at all. For example the listing of agoras supports this. This is useful and handy if you just want to request some generic information.

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

Currently the user token is currently only accesible through administrators that can access to the django shell:

.. code-block:: python

    In [1]: from tastypie.models import ApiKey

    In [2]: ApiKey.objects.get(user__username="user1")
    Out[2]: <ApiKey: b133b30b2348d7ba8ac6cb63b7aefb382c0804d2 for user1>



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
               "election_type": "ONE_CHOICE",
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
               "election_type": "ONE_CHOICE",
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
               "election_type": "ONE_CHOICE",
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
               "election_type": "ONE_CHOICE",
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
        "election_type": "ONE_CHOICE",
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

Create new agora
----------------

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
        "election_type": "ONE_CHOICE",
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

.. http:put:: /agora/(int:agora_id)

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
        "election_type": "ONE_CHOICE",
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

Execute an action
-----------------

.. http:post:: /agora/(int:agora_id)/action

   Request to execute an action in the agora (`agora_id`).

   The available actions are:

   **get_permissions**

   Returns a list of the permissions that the authenticated user has over the specified agora.

   **request_membership**

   The authenticated user requests membership in the specified agora. The authenticated user must have the ``request_membership`` permission on the agora to succeed.

   **join**

   The authenticated user joins the specified agora. The authenticated user must have the ``join`` permission on the agora to succeed.

   **leave**
   The authenticated user leaves the specified agora. The authenticated user must have the ``leave`` permission on the agora to succeed. The creator of an agora can leave it.

   **accept_membership**

   The authenticated user accepts the membership of the specified user (in the field "username") in an agora. The authenticated user must have ``admin`` permission on the agora and the specified user must have a pending membership request to succeed.

   **deny_membership**

   The authenticated user denies the membership of the specified user (in the field "username") in an agora. The authenticated user must have ``admin`` permission on the agora and the specified user must have a pending membership request to succeed.

   **add_membership**

   The authenticated user adds membership to the specified user (in the field "username") in an agora. The authenticated user must have ``admin`` permission on the agora and the specified username must be not a member of the given agora to succeed.

   **remove_membership**

   The authenticated user removes membership to the specified user (in the field "username") in an agora. The authenticated user must have ``admin`` permission on the agora and the specified username must be a member of the given agora to succeed.

   **request_admin_membership**

   The authenticated user requests admin membership in an agora. The authenticated user must have ``request_admin_membership`` permission on the agora to succeed.

   **accept_admin_membership**

   The authenticated user accepts admin membership to the specified user (in the field "username") in an agora. The authenticated user must have ``admin`` permission on the agora and the specified username must have a pending admin membership request in the given agora to succeed.

   **deny_admin_membership**

   The authenticated user denies admin membership to the specified user (in the field "username") in an agora. The authenticated user must have ``admin`` permission on the agora and the specified username must have a pending admin membership request in the given agora to succeed.

   **add_admin_membership**

   The authenticated user adds admin membership to the specified user (in the field "username") in an agora. The authenticated user must have ``admin`` permission on the agora and the specified username must be a member in the given agora to succeed.

   **remove_admin_membership**

   The authenticated user removes admin membership from the specified user (in the field "username") in an agora. The authenticated user must have ``admin`` permission on the agora and the specified username must be a member in the given agora to succeed.

   **leave_admin_membership**

   The authenticated user leaves admin membership in an agora. The authenticated user must have ``admin`` permission on the given agora to succeed.

   **create_election**

   The authenticated creates an election in the given agora, providing the following fields:
    * **question**: a text with the main question in the election. Required.
    * **answers**: a list with at least two possible answers to the question. required.
    * **pretty_name**: A title for the election. Required.
    * **description**: A description text for the election. It can follow restructured text format and be as large as needed. Required.
    * **is_vote_secret**: A boolean specifiying if the direct votes must all be secret or not. Required.
    * **from_date**: A string representing the starting date of the election, in format '%Y-%m-%dT%H:%M:%S'. Optional. 
    * **to_date**: A string representing the end date of the election, in format '%Y-%m-%dT%H:%M:%S'. Optional. 

   **delegate_vote**

   The authenticated user stablishes the delegation to an user specified in the field "username", cancelling the previous delegation if any from now on. The authenticated user must have  ``delegate`` permission on the agora and the specified username must exists to succeed.

   **cancel_vote_delegation**

   The authenticated user cancels its delegation on the specified agora from now on. The authenticated user must have  ``delegate`` permission on the agora and have a current delegate on the specified agora to succeed.

   :param agora_id: agora's unique id
   :type agora_id: int
   :form action: name of the action. Required.
   :status 200 OK: no error
   :statuscode 403 FORBIDDEN: when the user has not the required permissions
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/agora/1/action/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript
    Authorization: ApiKey linus:204db7bcfafb2deb7506b89eb3b9b715b09905c8

    {
       "action": "add_membership",
       "username": "foobar"
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "status": "success"
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
               "username": "user1",
               "agora_permissions": []
           },
           {
               "date_joined": "2012-12-18T15:46:37.644236",
               "first_name": "Maria Moreno",
               "id": 5,
               "is_active": true,
               "last_login": "2012-12-18T15:55:12.833627",
               "last_name": "",
               "username": "user4",
               "agora_permissions": []
           }
       ]
    }

List administrators
-------------------

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
               "username": "user1",
               "agora_permissions": []
           }
       ]
    }

List membership requests
------------------------

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
               "username": "user6",
               "agora_permissions": []
           }
       ]
    }

Retrieve agora admin membership requests
----------------------------------------

.. http:get:: /agora/(int:agora_id)/admin_membership_requests

   Retrieves the users that have pending requests to become admins of agora (`agora_id`). The authenticated user must be an administrator.

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 403 FORBIDDEN: when the user has no admin permissions
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/admin_membership_requests/ HTTP/1.1
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
               "username": "user6",
               "agora_permissions": []
           }
       ]
    }

List active delegates
---------------------

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
               "username": "user3",
               "agora_permissions": []
           }
       ]
    }

List all elections
------------------

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
               "extra_data": 
               {
                   "started": true
               },
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
               "questions": 
               [
                   {
                       "a": "ballot/question",
                       "min": 0,
                       "max": 1,
                       "tally_type": "simple",
                       "question": "question of election 2",
                       "answers": 
                       [
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "yes"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "no"
                           }
                       ],
                       "randomize_answer_order": true
                   }
               ],
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

List tallied elections
----------------------

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
               "delegated_votes_result": 
               {
                   "delegation_counts": 
                   [
                   ],
                   "a": "result",
                   "election_counts":
                   [
                       [
                           0,
                           0,
                           0
                       ]
                   ]
               },
               "description": "this is election 3",
               "election_type": "ONE_CHOICE",
               "electorate":
               [
                   "/api/v1/user/2/",
                   "/api/v1/user/5/"
               ],
               "eligibility": "",
               "extra_data": 
               {
                   "started": true,
                   "ended": true
               },
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
               "questions":
               [
                   {
                       "a": "ballot/question",
                       "min": 0,
                       "max": 1,
                       "tally_type": "simple",
                       "question": "question of election 3",
                       "answers":
                       [
                           {
                               "a": "ballot/answer",
                               "by_delegation_count": 0,
                               "url": "",
                               "by_direct_vote_count": 0,
                               "value": "a",
                               "details": ""
                           },
                           {
                               "a": "ballot/answer",
                               "by_delegation_count": 0,
                               "url": "",
                               "by_direct_vote_count": 1,
                               "value": "b",
                               "details": ""
                           },
                           {
                               "a": "ballot/answer",
                               "by_delegation_count": 0,
                               "url": "",
                               "by_direct_vote_count": 1,
                               "value": "c",
                               "details": ""
                           }
                       ],
                       "randomize_answer_order": true
                   }
               ],
               "resource_uri": "/api/v1/election/5/",
               "result":
               [
                   {
                       "a": "ballot/question",
                       "min": 0,
                       "max": 1,
                       "tally_type": "simple",
                       "question": "question of election 3",
                       "answers":
                       [
                           {
                               "a": "ballot/answer",
                               "by_delegation_count": 0,
                               "url": "",
                               "by_direct_vote_count": 0,
                               "value": "a",
                               "details": ""
                           },
                           {
                               "a": "ballot/answer",
                               "by_delegation_count": 0,
                               "url": "",
                               "by_direct_vote_count": 1,
                               "value": "b",
                               "details": ""
                           },
                           {
                               "a": "ballot/answer",
                               "by_delegation_count": 0,
                               "url": "",
                               "by_direct_vote_count": 1,
                               "value": "c",
                               "details": ""
                           }
                       ],
                       "randomize_answer_order": true
                   }
               ],
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

List open elections
-------------------

.. http:get:: /agora/(int:agora_id)/open_elections

   Retrieves open elections in agora (`agora_id`): elections that are currently
   taking place in the agora.

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
                "extra_data": 
                {
                    "started": true
                },
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
                "questions": 
                [
                    {
                        "a": "ballot/question",
                        "tally_type": "simple",
                        "max": 1,
                        "min": 0,
                        "question": "question of election 1",
                        "answers": 
                        [
                            {
                                "a": "ballot/answer",
                                "url": "",
                                "details": "",
                                "value": "one"
                            },
                            {
                                "a": "ballot/answer",
                                "url": "",
                                "details": "",
                                "value": "two"
                            },
                            {
                                "a": "ballot/answer",
                                "url": "",
                                "details": "",
                                "value": "three"
                            }
                        ],
                        "randomize_answer_order": true
                    }
                ],
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


List requested elections
------------------------

.. http:get:: /agora/(int:agora_id)/requested_elections

   Retrieves requested elections in agora (`agora_id`): elections that have
   been created and requested to take place in the agora but have not been
   approved yet.

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/requested_elections/ HTTP/1.1
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
               "extra_data":
               {
                   "started": true
               },
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
               "questions": 
               [
                   {
                       "a": "ballot/question",
                       "tally_type": "simple",
                       "max": 1,
                       "min": 0,
                       "question": "question of election 1",
                       "answers":
                       [
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "one"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "two"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "three"
                           }
                       ],
                       "randomize_answer_order": true
                   }
               ],
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

List archived elections
-----------------------

.. http:get:: /agora/(int:agora_id)/archived_elections

   Retrieves archived elections in agora (`agora_id`): elections that have
   been archived/discarded in the agora.

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/archived_elections/ HTTP/1.1
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
               "extra_data":
               {
                   "started": true
               },
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
               "questions": 
               [
                   {
                       "a": "ballot/question",
                       "tally_type": "simple",
                       "max": 1,
                       "min": 0,
                       "question": "question of election 1",
                       "answers":
                       [
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "one"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "two"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "three"
                           }
                       ],
                       "randomize_answer_order": true
                   }
               ],
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

List approved elections
-----------------------

.. http:get:: /agora/(int:agora_id)/approved_elections

   Retrieves approved elections in agora (`agora_id`): elections that have
   administrators" approval to take place in the agora.

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/approved_elections/ HTTP/1.1
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
               "extra_data":
               {
                   "started": true
               },
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
               "questions": 
               [
                   {
                       "a": "ballot/question",
                       "tally_type": "simple",
                       "max": 1,
                       "min": 0,
                       "question": "question of election 1",
                       "answers": 
                       [
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "one"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "two"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "three"
                           }
                       ],
                       "randomize_answer_order": true
                   }
               ],
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


Comments
--------

.. http:get:: /agora/(int:agora_id)/comments

   Retrieves comments in agora (`agora_id`)

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/agora/1/comments/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "meta":{
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":[
            {
                "geolocation":
                [
                    0,
                    0
                ],
                "description":"",
                "timestamp":"2013-03-31T11:15:20.753223",
                "type_name":"target_agora_action_object_comment",
                "actor":
                {
                    "username":"david",
                    "first_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "content_type":"user",
                    "id":0
                },
                "public":true,
                "verb":"commented",
                "vote":
                {

                },
                "action_object":
                {
                    "comment":"foo comment",
                    "id":1,
                    "content_type":"comment"
                },
                "id":1,
                "target":
                {
                    "mugshot_url":"/static/img/agora_default_logo.png",
                    "name":"agoraone",
                    "url":"/david/agoraone",
                    "pretty_name":"AgoraOne",
                    "content_type":"agora",
                    "full_name":"david/agoraone",
                    "short_description":"AgoraOne",
                    "id":1
                }
            }
        ]
    }

Add comment
-----------

.. http:post:: /agora/(int:agora_id)/add_comment

   Adds a new comment in agora (`agora_id`) with the authenticated user. The user must be authenticated and have ``comment`` permission.

   :param agora_id: agora's unique id
   :type agora_id: int
   :status 200 OK: no error
   :status 403 FORBIDDEN: when the user is not authenticated or has not permission
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/agora/1/add_comment/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript
    Authorization: ApiKey daniel:204db7bcfafb2deb7506b89eb3b9b715b09905c8

    {
        "comment": "foo comment"
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8


    {
        "meta":
        {
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":
        [
            {
                "geolocation":
                [
                    0,
                    0
                ],
                "description":"",
                "timestamp":"2013-03-31T11:15:20.753223",
                "type_name":"target_agora_action_object_comment",
                "actor":
                {
                    "username":"david",
                    "first_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "content_type":"user",
                    "id":0
                },
                "public":true,
                "verb":"commented",
                "vote":
                {

                },
                "action_object":
                {
                    "comment":"foo comment",
                    "id":1,
                    "content_type":"comment"
                },
                "id":1,
                "target":
                {
                    "mugshot_url":"/static/img/agora_default_logo.png",
                    "name":"agoraone",
                    "url":"/david/agoraone",
                    "pretty_name":"AgoraOne",
                    "content_type":"agora",
                    "full_name":"david/agoraone",
                    "short_description":"AgoraOne",
                    "id":1
                }
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

   Login in the application using session. It's only used in web requests.

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
   :status 400 BAD REQUEST: when the username isn"t available

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/user/username_available/?username=danigm HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

Reset Password 
--------------

.. http:post:: /user/password_reset/

   Given the email of an user, sends an email with a reset password link to that user.

   :status 200 OK: when everything is ok
   :status 400 BAD REQUEST: when email given is not one of an existing user

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/user/password_reset/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

    {
        "email": "david@david.com"
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "objects":[
            {
                "username":"david",
                "first_name":"",
                "last_name":"",
                "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                "url":"/user/david",
                "is_active":true,
                "last_login":"2012-11-29T17:18:46.837000",
                "short_description":"Is a member of 2 agoras and has emitted  0 direct votes.",
                "id":0,
                "date_joined":"2012-11-29T15:08:43.874000"
            }
        ]
    }

Disable current user
--------------------

.. http:post:: /user/disable/

   Disable the currently authenticated user.

   :status 200 OK: when everything is ok
   :status 400 METHOD NOT ALLOWED: when email given is not one of an existing user

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/user/disable/ HTTP/1.1
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
               "election_type": "ONE_CHOICE",
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
               "election_type": "ONE_CHOICE",
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
               "election_type": "ONE_CHOICE",
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
               "election_type": "ONE_CHOICE",
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


List agoras of a given user
---------------------------

.. http:get:: /user/(int:userid)/agoras/

   List agoras of the user with (`userid`).

   :query offset: offset number. default is 0
   :query limit: limit number. default is 20
   :statuscode 200 OK: no error
   :statuscode 404 NOT FOUND: the requested user does not exist

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/user/(int:userid)/agoras/ HTTP/1.1
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
          "total_count":2,
          "limit":20,
          "offset":0
       },
       "objects":
       [
          {
	     "membership_policy":"ANYONE_CAN_JOIN",
	     "mugshot_url":"/static/img/agora_default_logo.png",
	     "name":"agoraone",
	     "creator":
             {
	        "username":"david",
	        "first_name":"",
	        "last_name":"",
	        "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
	        "url":"/user/david",
	        "is_active":true,
	        "last_login":"2012-11-29T17:18:46.837000",
	        "short_description":"Is a member of 2 agoras and has emitted  0 direct votes.",
	        "id":0,
	        "date_joined":"2012-11-29T15:08:43.874000"
	     },
	     "eligibility":"",
	     "comments_policy":"ANYONE_CAN_COMMENT",
	     "id":1,
	     "pretty_name":"AgoraOne",
	     "url":"/david/agoraone",
	     "created_at_date":"2013-03-31T14:55:15.004828",
	     "archived_at_date":null,
	     "full_name":"david/agoraone",
	     "short_description":"AgoraOne",
	     "image_url":"",
	     "extra_data":"",
	     "is_vote_secret":false,
	     "election_type":"ONCE_CHOICE",
	     "biography":""
          },
          {
	     "membership_policy":"ANYONE_CAN_JOIN",
	     "mugshot_url":"/static/img/agora_default_logo.png",
	     "name":"agoratwo",
	     "creator":
             {
	        "username":"david",
	        "first_name":"",
	        "last_name":"",
	        "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
	        "url":"/user/david",
	        "is_active":true,
	        "last_login":"2012-11-29T17:18:46.837000",
	        "short_description":"Is a member of 2 agoras and has emitted  0 direct votes.",
	        "id":0,
	        "date_joined":"2012-11-29T15:08:43.874000"
	     },
	     "eligibility":"",
	     "comments_policy":"ANYONE_CAN_COMMENT",
	     "id":2,
	     "pretty_name":"AgoraTwo",
	     "url":"/david/agoratwo",
	     "created_at_date":"2013-03-31T14:55:15.019918",
	     "archived_at_date":null,
	     "full_name":"david/agoratwo",
	     "short_description":"AgoraTwo",
	     "image_url":"",
	     "extra_data":"",
	     "is_vote_secret":true,
	     "election_type":"ONCE_CHOICE",
	     "biography":""
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
               "election_type": "ONE_CHOICE",
               "electorate":
               [
               ],
               "eligibility": "",
               "extra_data":
               {
                   "started": true
               },
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
               "percentage_of_participation": 22,
               "pretty_name": "Votación de prueba",
               "questions":
               [
                   {
                       "a": "ballot/question",
                       "tally_type": "simple",
                       "max": 1,
                       "min": 0,
                       "question":
                       "question of election 1",
                       "answers":
                       [
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "one"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "two"
                           },
                           {
                               "a": "ballot/answer",
                               "url": "",
                               "details": "",
                               "value": "three"
                           }
                       ],
                       "randomize_answer_order": true
                   }
               ],
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


List of valid usernames
-----------------------

.. http:get:: user/set_username/(string:username1);(string:username2);.../

   List of users from the requested list of usernames (`username1`, `username2`, etc). Only usernames referring to existing users will be listed.

   :statuscode 200 OK: no error
   :statuscode 403 FORBIDDEN: when the user is not authenticated

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/user/set_username/david;user1/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "objects":
        [
            {
                "username":"david",
                "first_name":"",
                "last_name":"",
                "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                "url":"/user/david",
                "is_active":true,
                "last_login":"2012-11-29T17:18:46.837000",
                "short_description":"Is a member of 2 agoras and has emitted  0 direct votes.",
                "id":0,
                "date_joined":"2012-11-29T15:08:43.874000"
            },
            {
                "username":"user1",
                "first_name":"Juana Molero",
                "last_name":"",
                "mugshot_url":"http://www.gravatar.com/avatar/cc721459f5b77680bc6a8ba6c9681c46?s=50&d=identicon",
                "url":"/user/user1",
                "is_active":true,
                "last_login":"2012-11-29T18:37:36.263000",
                "short_description":"ultricies. semper vel et, eu laoreet Quisque odio semper ornare. elementum elementum tristique pretium ornare",
                "id":1,
                "date_joined":"2012-11-29T18:37:36.263000"
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
   :query model: filtering by object type, not required. Possible values are: ``agora``, ``election``, ``castvote``.
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

Resource: Election
==================

This resource represents an election


.. http:get:: /election/

   Lists elections

   :query offset: offset number. default is 0
   :query limit: limit number. default is 20
   :statuscode 200 OK: no error

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/election/ HTTP/1.1
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
            "previous":null,
            "total_count":1,
            "offset":0,
            "limit":20,
            "next":null
        },
        "objects":
        [
            {
                "creator":"/api/v1/user/0/",
                "comments_policy":"ANYONE_CAN_COMMENT",
                "result_tallied_at_date":null,
                "result":"",
                "mugshot_url":"/static/img/election_new_form_info.png",
                "id":5,
                "voting_extended_until_date":null,
                "is_approved":true,
                "last_modified_at_date":"2012-12-06T18:17:14.457000",
                "direct_votes_count":0,
                "short_description":"election three",
                "extra_data":"",
                "questions":
                [
                    {
                        "a": "ballot/question",
                        "tally_type": "simple",
                        "max": 1,
                        "min": 0,
                        "question": "question three",
                        "answers":
                        [
                            {
                                "a": "ballot/answer",
                                "url": "",
                                "details": "",
                                "value": "one"
                            },
                            {
                                "a": "ballot/answer",
                                "url": "",
                                "details": "",
                                "value": "two"
                            },
                            {
                                "a": "ballot/answer",
                                "url": "",
                                "details": "",
                                "value": "three"
                            }
                        ],
                        "randomize_answer_order": true
                    }
                ],
                "is_vote_secret":false,
                "voters_frozen_at_date":null,
                "hash":null,
                "description":"election three",
                "frozen_at_date":null,
                "eligibility":"",
                "parent_election":null,
                "pretty_name":"electionthree",
                "delegated_votes_result":"",
                "uuid":"a7be018c-2111-419b-b9b8-c78fd0bc9912",
                "delegated_votes_count":0,
                "percentage_of_participation":0,
                "name":"electionthree",
                "delegated_votes_frozen_at_date":null,
                "url":"/david/agoratwo/election/electionthree",
                "voting_ends_at_date":null,
                "approved_at_date":null,
                "tiny_hash":null,
                "created_at_date":"2012-12-06T18:17:14.446000",
                "agora":
                {
                    "mugshot_url":"/static/img/agora_default_logo.png",
                    "name":"agoratwo",
                    "url":"/david/agoratwo",
                    "pretty_name":"AgoraTwo",
                    "content_type":"agora",
                    "full_name":"david/agoratwo",
                    "short_description":"AgoraTwo",
                    "id":2
                },
                "voting_starts_at_date":null,
                "election_type":"ONCE_CHOICE",
                "archived_at_date":null
            }
        ]
    }

Retrieve an election
--------------------

.. http:get:: /election/(int:election_id)

   Retrieves an election (`election_id`).

   :param election_id: election's unique id
   :type election_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the election is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/election/5/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "creator":"/api/v1/user/0/",
        "comments_policy":"ANYONE_CAN_COMMENT",
        "result_tallied_at_date":null,
        "result":"",
        "mugshot_url":"/static/img/election_new_form_info.png",
        "id":5,
        "voting_extended_until_date":null,
        "is_approved":true,
        "last_modified_at_date":"2012-12-06T18:17:14.457000",
        "direct_votes_count":0,
        "short_description":"election three",
        "extra_data":"",
        "questions":
        [
            {
                "a": "ballot/question",
                "tally_type": "simple",
                "max": 1, "min": 0,
                "question": "question three",
                "answers":
                [
                    {
                        "a": "ballot/answer",
                        "url": "",
                        "details": "",
                        "value": "one"
                    },
                    {
                        "a": "ballot/answer",
                        "url": "",
                        "details": "",
                        "value": "two"
                    },
                    {
                        "a": "ballot/answer",
                        "url": "",
                        "details": "",
                        "value": "three"
                    }
                ],
                "randomize_answer_order": true
            }
        ],
        "is_vote_secret":false,
        "voters_frozen_at_date":null,
        "hash":null,
        "description":"election three",
        "frozen_at_date":null,
        "eligibility":"",
        "parent_election":null,
        "pretty_name":"electionthree",
        "delegated_votes_result":"",
        "uuid":"a7be018c-2111-419b-b9b8-c78fd0bc9912",
        "delegated_votes_count":0,
        "percentage_of_participation":0,
        "name":"electionthree",
        "delegated_votes_frozen_at_date":null,
        "url":"/david/agoratwo/election/electionthree",
        "voting_ends_at_date":null,
        "approved_at_date":null,
        "tiny_hash":null,
        "created_at_date":"2012-12-06T18:17:14.446000",
        "agora":
        {
            "mugshot_url":"/static/img/agora_default_logo.png",
            "name":"agoratwo",
            "url":"/david/agoratwo",
            "pretty_name":"AgoraTwo",
            "content_type":"agora",
            "full_name":"david/agoratwo",
            "short_description":"AgoraTwo",
            "id":2
        },
        "voting_starts_at_date":null,
        "election_type":"ONCE_CHOICE",
        "archived_at_date":null
    }


Modify election
---------------

.. http:put:: /agora/(int:election_id)/

   Modifies an election (`election_id`). Requires the authenticated user to be election administrator. All the parameters are optional: you only need to suply the parameters you want to change.

   :form question: a text with the main question in the election. 
   :form answers: a list with at least two possible answers to the question.
   :form pretty_name: A title for the election. 
   :form description: A description text for the election. It can follow restructured text format and be as large as needed. 
   :form is_vote_secret: A boolean specifiying if the direct votes must all be secret or not. 
   :form from_date: A string representing the starting date of the election, in format '%Y-%m-%dT%H:%M:%S'.
   :form to_date: A string representing the end date of the election, in format '%Y-%m-%dT%H:%M:%S'.
   :status 202 CREATED: when agora is modified correctly
   :status 403 FORBIDDEN: when the user has no agora administration permissions
   :status 400 BAD REQUEST: when the form parameters are invalid

   .. sourcecode:: http

    PUT /api/v1/agora/5/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

    {
        "from_date": "2020-02-18T20:13:00"
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 202 ACCEPTED
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8


    {
        "creator":"/api/v1/user/0/",
        "comments_policy":"ANYONE_CAN_COMMENT",
        "result_tallied_at_date":null,
        "result":"",
        "mugshot_url":"/static/img/election_new_form_info.png",
        "id":5,
        "voting_extended_until_date":null,
        "is_approved":true,
        "last_modified_at_date":"2013-03-27T20:17:14.457000",
        "direct_votes_count":0,
        "short_description":"election three",
        "extra_data":"",
        "questions":
        [
            {
                "a": "ballot/question",
                "tally_type": "simple",
                "max": 1,
                "min": 0,
                "question": "question three",
                "answers":
                [
                    {
                        "a": "ballot/answer",
                        "url": "", "details": "",
                        "value": "one"
                    },
                    {
                        "a": "ballot/answer",
                        "url": "",
                        "details": "",
                        "value": "two"
                    },
                    {
                        "a": "ballot/answer",
                        "url": "",
                        "details": "",
                        "value": "three"
                    }
                ],
                "randomize_answer_order": true
            }
        ],
        "is_vote_secret":false,
        "voters_frozen_at_date":null,
        "hash":null,
        "description":"election three",
        "frozen_at_date":null,
        "eligibility":"",
        "parent_election":null,
        "pretty_name":"electionthree",
        "delegated_votes_result":"",
        "uuid":"a7be018c-2111-419b-b9b8-c78fd0bc9912",
        "delegated_votes_count":0,
        "percentage_of_participation":0,
        "name":"electionthree",
        "delegated_votes_frozen_at_date":null,
        "url":"/david/agoratwo/election/electionthree",
        "voting_ends_at_date":null,
        "approved_at_date":null,
        "tiny_hash":null,
        "created_at_date":"2012-12-06T18:17:14.446000",
        "agora":
        {
            "mugshot_url":"/static/img/agora_default_logo.png",
            "name":"agoratwo",
            "url":"/david/agoratwo",
            "pretty_name":"AgoraTwo",
            "content_type":"agora",
            "full_name":"david/agoratwo",
            "short_description":"AgoraTwo",
            "id":2
        },
        "voting_starts_at_date": "2020-02-18T20:13:00",
        "election_type":"ONCE_CHOICE",
        "archived_at_date":null
    }

List all votes
--------------

.. http:get:: /election/(int:election_id)/all_votes

   Lists all votes in the election (`election_id`)

   :param election_id: election's unique id
   :type election_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the election is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/election/5/all_votes/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "meta":{
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":
        [
            {
                "voter":
                {
                    "username":"david",
                    "first_name":"",
                    "last_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "is_active":true,
                    "last_login":"2013-03-31T13:35:46.210302",
                    "short_description":"Is a member of 2 agoras and has emitted  1 direct votes.",
                    "id":0,
                    "date_joined":"2012-11-29T15:08:43.874000"
                },
                "hash":"e33826075d8b5a6d2741699604d6ecaf0d3eda02f6ccbf4664ef0a70267f8532",
                "public_data":
                {
                },
                "casted_at_date":"2013-03-31T13:35:46.571346",
                "is_counted":true,
                "is_direct":true,
                "invalidated_at_date":null,
                "reason":"",
                "election":"/api/v1/election/6/",
                "tiny_hash":null,
                "is_public":false,
                "id":1,
                "action_id":3
            }
        ]
    }

List cast votes
---------------

.. http:get:: /election/(int:election_id)/cast_votes

   Lists cast votes in the election (`election_id`)

   :param election_id: election's unique id
   :type election_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the election is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/election/5/cast_votes/ HTTP/1.1
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
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":
        [
            {
                "voter":
                {
                    "username":"david",
                    "first_name":"",
                    "last_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "is_active":true,
                    "last_login":"2013-03-31T13:35:46.210302",
                    "short_description":"Is a member of 2 agoras and has emitted  1 direct votes.",
                    "id":0,
                    "date_joined":"2012-11-29T15:08:43.874000"
                },
                "hash":"e33826075d8b5a6d2741699604d6ecaf0d3eda02f6ccbf4664ef0a70267f8532",
                "public_data":
                {
                },
                "casted_at_date":"2013-03-31T13:35:46.571346",
                "is_counted":true,
                "is_direct":true,
                "invalidated_at_date":null,
                "reason":"",
                "election":"/api/v1/election/6/",
                "tiny_hash":null,
                "is_public":false,
                "id":1,
                "action_id":3
            }
        ]
    }

List delegated votes
--------------------

.. http:get:: /election/(int:election_id)/delegated_votes

   Lists delegated votes in the election (`election_id`)

   :param election_id: election's unique id
   :type election_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the election is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/election/5/delegated_votes/ HTTP/1.1
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
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":
        [
            {
                "voter":
                {
                    "username":"david",
                    "first_name":"",
                    "last_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "is_active":true,
                    "last_login":"2013-03-31T13:35:46.210302",
                    "short_description":"Is a member of 2 agoras and has emitted  1 direct votes.",
                    "id":0,
                    "date_joined":"2012-11-29T15:08:43.874000"
                },
                "hash":"e33826075d8b5a6d2741699604d6ecaf0d3eda02f6ccbf4664ef0a70267f8532",
                "public_data":
                {
                },
                "casted_at_date":"2013-03-31T13:35:46.571346",
                "is_counted":true,
                "is_direct":true,
                "invalidated_at_date":null,
                "reason":"",
                "election":"/api/v1/election/6/",
                "tiny_hash":null,
                "is_public":false,
                "id":1,
                "action_id":3
            }
        ]
    }

List votes from delegates
-------------------------

.. http:get:: /election/(int:election_id)/votes_from_delegates

   Lists votes from delegates in the election (`election_id`)

   :param election_id: election's unique id
   :type election_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the election is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/election/5/votes_from_delegates/ HTTP/1.1
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
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":
        [
            {
                "voter":
                {
                    "username":"david",
                    "first_name":"",
                    "last_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "is_active":true,
                    "last_login":"2013-03-31T13:35:46.210302",
                    "short_description":"Is a member of 2 agoras and has emitted  1 direct votes.",
                    "id":0,
                    "date_joined":"2012-11-29T15:08:43.874000"
                },
                "hash":"e33826075d8b5a6d2741699604d6ecaf0d3eda02f6ccbf4664ef0a70267f8532",
                "public_data":
                {
                },
                "casted_at_date":"2013-03-31T13:35:46.571346",
                "is_counted":true,
                "is_direct":true,
                "invalidated_at_date":null,
                "reason":"",
                "election":"/api/v1/election/6/",
                "tiny_hash":null,
                "is_public":false,
                "id":1,
                "action_id":3
            }
        ]
    }

Direct votes
------------

.. http:get:: /election/(int:election_id)/direct_votes

   Lists direct votes in the election (`election_id`)

   :param election_id: election's unique id
   :type election_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the election is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/election/5/direct_votes/ HTTP/1.1
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
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":
        [
            {
                "voter":
                {
                    "username":"david",
                    "first_name":"",
                    "last_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "is_active":true,
                    "last_login":"2013-03-31T13:35:46.210302",
                    "short_description":"Is a member of 2 agoras and has emitted  1 direct votes.",
                    "id":0,
                    "date_joined":"2012-11-29T15:08:43.874000"
                },
                "hash":"e33826075d8b5a6d2741699604d6ecaf0d3eda02f6ccbf4664ef0a70267f8532",
                "public_data":
                {
                },
                "casted_at_date":"2013-03-31T13:35:46.571346",
                "is_counted":true,
                "is_direct":true,
                "invalidated_at_date":null,
                "reason":"",
                "election":"/api/v1/election/6/",
                "tiny_hash":null,
                "is_public":false,
                "id":1,
                "action_id":3
            }
        ]
    }


List comments
-------------

.. http:get:: /election/(int:election_id)/comments

   Retrieves comments in election (`election_id`)

   :param election_id: election's unique id
   :type election_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the election is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/election/1/comments/ HTTP/1.1
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
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":
        [
            {
                "geolocation":
                [
                    0,
                    0
                ],
                "description":"",
                "timestamp":"2013-03-31T11:15:20.753223",
                "type_name":"target_agora_action_object_comment",
                "actor":
                {
                    "username":"david",
                    "first_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "content_type":"user",
                    "id":0
                },
                "public":true,
                "verb":"commented",
                "vote":
                {

                },
                "action_object":
                {
                    "comment":"foo comment",
                    "id":1,
                    "content_type":"comment"
                },
                "id":1,
                "target":
                {
                    "agora":
                    {
                        "content_type":"agora",
                        "full_name":"admin/muahaha",
                        "id":7,
                        "mugshot_url":"/static/img/agora_default_logo.png",
                        "name":"muahaha",
                        "pretty_name":"muahaha",
                        "short_description":"yeah",
                        "url":"/admin/muahaha"
                    },
                    "content_type":"election",
                    "id":1,
                    "mugshot_url":"/static/img/election_new_form_info.png",
                    "name":"aaaaaaaaaaaa",
                    "pretty_name":"aaaaaaaaaaaa",
                    "short_description":"aaaaaaaaaaaaaaaa",
                    "url":"/admin/muahaha/election/aaaaaaaaaaaa"
                },
            }
        ]
    }

Add comment
-----------

.. http:post:: /election/(int:election_id)/add_comment

   Adds a new comment in election (`election_id`) with the authenticated user. The user must be authenticated and have ``comment`` permission.

   :param election_id: election's unique id
   :type election_id: int
   :status 200 OK: no error
   :status 403 FORBIDDEN: when the user is not authenticated or has not permission
   :status 404 NOT FOUND: when the election is not found

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/election/1/add_comment/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript
    Authorization: ApiKey daniel:204db7bcfafb2deb7506b89eb3b9b715b09905c8

    {
        "comment": "foo comment"
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8


    {
        "meta":
        {
            "total_count":1,
            "limit":20,
            "offset":0
        },
        "objects":
        [
            {
                "geolocation":"[0, 0]",
                "description":"",
                "timestamp":"2013-03-31T11:15:20.753223",
                "type_name":"target_agora_action_object_comment",
                "actor":
                {
                    "username":"david",
                    "first_name":"",
                    "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
                    "url":"/user/david",
                    "content_type":"user",
                    "id":0
                },
                "public":true,
                "verb":"commented",
                "vote":
                {

                },
                "action_object":
                {
                    "comment":"foo comment",
                    "id":1,
                    "content_type":"comment"
                },
                "id":1,
                "target":
                {
                    "agora":
                    {
                        "content_type":"agora",
                        "full_name":"admin/muahaha",
                        "id":7,
                        "mugshot_url":"/static/img/agora_default_logo.png",
                        "name":"muahaha",
                        "pretty_name":"muahaha",
                        "short_description":"yeah",
                        "url":"/admin/muahaha"
                    },
                    "content_type":"election",
                    "id":1,
                    "mugshot_url":"/static/img/election_new_form_info.png",
                    "name":"aaaaaaaaaaaa",
                    "pretty_name":"aaaaaaaaaaaa",
                    "short_description":"aaaaaaaaaaaaaaaa",
                    "url":"/admin/muahaha/election/aaaaaaaaaaaa"
                },
            }
        ]
    }


Execute an action
-----------------

.. http:post:: /election/(int:election_id)/action

   Request to execute an action in the election (`election_id`).

   The available actions are:

   **get_permissions**

   Returns a list of the permissions that the authenticated user has over the specified election.

   **approve**

   Approves the election. The authenticated user must have ``approve_election`` permission on the election and the election must have be pending approval.

   **start**

   Starts the election, so that the electorate can start voting on it. The authenticated user must have ``begin_election`` permission on the election.

   **stop**

   Stops the voting period of the election. The authenticated user must have ``end_election`` permission on the election.

   **archive**

   Archives the election. The authenticated user must have ``archive_election`` permission on the election.

   **vote**

   The authenticated emits a direct vote in this election, providing the following fields:
    * **is_vote_secret**: boolean indicating if the vote is public (and thus subject to delegation) or not. Required.
    * **reason**: a reason for the vote. Conditional, used only for public votes.
    * **question0**: string containing the chosen option for the question. Required.
 
   User must have ``emit_direct_vote`` permission to succeed. A single user can vote multiple times in one election, but only the last vote will remain valid.

   **cancel_vote**

   The authenticated user cancels its direct vote in the election. User must have ``emit_direct_vote`` permission and a valid current vote in the election to succeed.

   :param agora_id: agora's unique id
   :type agora_id: int
   :form action: name of the action. Required.
   :status 200 OK: no error
   :statuscode 403 FORBIDDEN: when the user has not the required permissions
   :status 404 NOT FOUND: when the agora is not found

   **Example request**:

   .. sourcecode:: http

    POST /api/v1/election/1/action/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript
    Authorization: ApiKey linus:204db7bcfafb2deb7506b89eb3b9b715b09905c8

    {
        "is_vote_secret": true,
        "question0": "Yay",
        "action": "vote"
    }

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "status": "success"
    }


Resource: CastVote
==================

Represents a vote in an election.

Retrieve a vote
---------------

.. http:get:: /cast_vote/(int:castvote_id)

   Retrieves a vote (`castvote_id`).

   :param castvote_id: vote's unique id
   :type castvote_id: int
   :status 200 OK: no error
   :status 404 NOT FOUND: when the vote is not found

   **Example request**:

   .. sourcecode:: http

    GET /api/v1/castvote/1/ HTTP/1.1
    Host: example.com
    Accept: application/json, text/javascript

   **Example response**:

   .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept, Accept-Language, Cookie
    Content-Type: application/json; charset=utf-8

    {
        "action_id":3,
        "casted_at_date":"2013-04-02T15:39:04.172499",
        "election":"/api/v1/election/6/",
        "hash":"b0ed7c90cd96cb0b15fa50b6a6fd2184c26d74e148a19abb1c3d8ed0ddabe060",
        "id":1,
        "invalidated_at_date":"2013-04-02T15:39:04.225578",
        "is_counted":false,
        "is_direct":true,
        "is_public":true,
        "public_data":
        {
            "a":"vote",
            "answers":
            [
                {
                    "a":"plaintext-answer",
                    "choices":
                    [
                        "Foobar"
                    ]
                }
            ],
            "election_hash":
            {
                "a":"hash/sha256/value",
                "value":"f9273dd65231e664281cd22880870e0c9cbcfa195e86460816b0fc1ecc97f7d1"
            },
            "election_uuid":"9f670e70-73c7-4e08-8ef1-5131bf39b1d5"
        },
        "reason":"becuase of .. yes",
        "tiny_hash":null,
        "voter":
        {
            "date_joined":"2012-11-29T15:08:43.874000",
            "first_name":"",
            "id":0,
            "is_active":true,
            "last_login":"2013-04-02T15:39:03.729283",
            "last_name":"",
            "mugshot_url":"http://www.gravatar.com/avatar/08d5c7923d841a23030038591c9ae3e0?s=50&d=identicon",
            "short_description":"Is a member of 2 agoras and has emitted  0 direct votes.",
            "url":"/user/david",
            "username":"david"
        }
    }

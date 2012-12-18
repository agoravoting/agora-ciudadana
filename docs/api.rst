=======
API
=======

Agora ciudadana exports a REST API with full access to the data model and user actions.

Format
======

Access to /api/v1/xxxx to use the API resources, using the corresponding HTTP methods (GET, POST, PUT, DELETE...).

Requests and answers may use any of the standard formats: xml, json or yaml. The format may be specified via "Accept"
HTTP headers or with ?format=json (or xml or yaml) parameter in the URL.


Authentication
==============

The API accepts two modes of authentication:

**Session authentication**

The session cookie used in the normal login is accepted and identifies the user that is using the API. This is useful
mainly for the javascript embedded in the own Agora pages.

**Token authentication**

For access the API with an external application, you need the auth token. When you call the login API function, the
user token is returned, and you must supply it in the Authorization header in all next HTTP calls:

.. code-block:: console

    # As a header
    # Format is ''Authorization: ApiKey <username>:<api_key>''
    Authorization: ApiKey daniel:204db7bcfafb2deb7506b89eb3b9b715b09905c8

**Status reporting**

API calls use the standard HTTP codes for status reporting (200 OK, 404 Not Found, 403 Forbidden, etc.). In case of
error, the returned data may have fields with additional info (see each individual call for more explanations).


Resource: Agora
===============

0 Resource fields
-----------------

* creator: User
* delegation_election: Election


1 Get agora list
----------------

* Description: get a list of all agoras, possibly filtered

* URL: agora/

* Method: GET

* Request format:

.. code-block:: console

    {username:"XXXXXXXX", password:"YYYYYYY"}

* Ejemplo de respuesta:

.. code-block:: console

    {success, auth_token: "XXXXXXXXXXXXXXXXXX"}


Resource: User
==============

 http:get:: /user/

   List users

   **Example request**:

   .. sourcecode:: http

    GET /user/ HTTP/1.1
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

   :query offset: offset number. default is 0
   :query limit: limit number. default is 20
   :statuscode 200: no error



Resource: Election
==================

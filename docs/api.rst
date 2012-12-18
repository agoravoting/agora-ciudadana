=======
API
=======

Agora ciudadana exports an API REST with full access to the data model and user actions.

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

For access the API with an external application, you need the token auth. When you call the login API function, the
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


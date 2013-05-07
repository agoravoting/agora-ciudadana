### Introduction

[![Build Status](https://api.travis-ci.org/agoraciudadana/agora-ciudadana.png?branch=v2)](https://travis-ci.org/agoraciudadana/agora-ciudadana)

Agora Ciudadana is a social web site where anyone can create or join in an agora.
An agora has a set of members which can vote in the agora's elections either by
direct vote or by delegating the vote.

You can see a live version of Agora here: https://agoravoting.com

The source code is available here: https://github.com/agoraciudadana/agora-ciudadana

You can have a glance at the development in our trello board: 
https://trello.com/board/agora-ciudadana/5054e9e060d5bc9a08196b96

Contact us in our developement mailing list:
https://groups.google.com/group/agora-ciudadana-devel

You can read the REST API Documentation in read the docs:
https://agora-ciudadana.readthedocs.org

### Installation instructions

The INSTALL.md file contains the detailed installation instructions

### Test instructions

To test the aplication you can use default django test system:

    $ ./runtests.sh

Or if you want to test only one test you can call:

    $ python manage.py test agora_core.AgoraTest.test_agora --settings=agora_site.test_settings

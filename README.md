### Introduction

Agora Ciudadana is a social web site where anyone can create or join in an agora.
An agora has a set of members which can vote in the agora's elections either by
direct vote or by delegating the vote.

You can see a  live version of Agora here: https://agoravoting.com

The source code is available here: http://github.com/agoraciudadana/agora-ciudadana

You can have a glance at the development in our trello board: 
https://trello.com/board/agora-ciudadana/5054e9e060d5bc9a08196b96

Contact us in our developement mailing list:
https://groups.google.com/group/agora-ciudadana-devel

### Installation instructions

The INSTALL file contains the detailed installation instructions

### Test instructions

To test the aplication you can use default django test system:

$ python manage.py test agora\_core

To test only one test case you can call:

$ python manage.py test agora\_core.AgoraTest

Or if you want to test only one test you can call:

$ python manage.py test agora\_core.AgoraTest.test\_agora

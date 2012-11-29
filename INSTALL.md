### Introduction

![Logo of Agora Ciudadana](https://agoravoting.com/static/img/agoralogo.png)

Agora Ciudadana is a social web site  where anyone can create or join in
an agora. An  agora has a set  of members which can vote  in the agora's
elections either by direct vote or by delegating the vote.


### Dependencies

* Python 2.x >= 2.6
* python-virtualenv
* python-celery (install with pip system-wide)
* rabbitmq-server
* python-xapian
* Has only been tested in Linux so far

Other dependencies can be installed with virtualenv.


### First installation

Here we will detail the most  simple way to get the application running.
For a more detailed explanation about  how to deploy a django, refer to:
http://docs.djangoproject.com/en/dev/topics/install/

First we need to create  the virtual environment where dependencies will
be installed:

```sh
$ ./virtualenv.py --system-site-packages env
```

Now everytime  we want to  use the installed  virtualenv, we can  do the
following within the directory containing the env/ subdirectory:

```sh
$ source env/bin/activate
```

Now we will install the dependencies:

```sh
$ pip install -r dependencies.txt --upgrade
```

In this  step you might  get the error  "fatal error: Python.h:  No such
file or directory". This happens for example in ubuntu. To fix that, you
need to install python-dev package. In Ubuntu/Debian you can do that:

```sh
$ sudo apt-get install python-dev
```

After that, we need to configure the database (we use sqlite by default):

```sh
$ ./manage.py syncdb --migrate --noinput
```

```sh
$ ./manage.py migrate
```

If you get an error saying something about xapin not installed, you need
to install  the package python-xapian.  In ubuntu it comes  installed by
default,

in openSUSE:

```sh
$ sudo zypper install python-xapian
```

In Debian/Ubuntu:

```sh
$ sudo apt-get install python-xapian
```

We use django  haystack for searching, so we need  to create the initial
index:

```sh
$ ./manage.py rebuild_index
```

We use celery and rabbitmq for programmed tasks, so you need to setup it
correctly in your server. Usually you just need to install it and run it
as a system daemon with:

```sh
$ sudo /etc/rc.d/rabbitmq start
```

And  then for  celery to  actually  process the  tasks sent  to it  (for
example start or stop an election), you need to run it as a daemon:

```sh
$ ./manage.py celeryd -l INFO -B -S djcelery.schedulers.DatabaseScheduler
```

That's it! Start the webserver with:

```sh
$ ./manage.py runserver
```

Now you'll be able to enter to Agora in http://localhost:8000

Of course  this is  a very  simple and  local installation.  We recomend
using a web server like cherokee, lighthttpd or apache configured to use
fast-cgi  and django,  and  a more  powerful  database like  postgresql.
Django documentation explains how to do that:

    [Django Install](http://docs.djangoproject.com/en/dev/topics/install/)

We also refer  to celery documentation for more details  on how to setup
them correctly in your server:

    [Celery Documentation](http://docs.celeryproject.org/en/latest/getting-started/brokers/rabbitmq.html)


### Translations

Agora Ciudadana  has internationalization  support and is  translated to
multiple languages.  In order  to make  these translations  available in
your installation, you need to compile the translation (.po) files:

```sh
$ ./manage.py compilemessages
```


### Settings configuration

The settings.py file contains the default configuration for the project.
You shouldn't modify  it; any settings configuration you  need should be
added to the custom_settings.py file.

Most  of  the  variables  in   settings  are  self-explanatory  and  are
documented in django: http://docs.djangoproject.com/en/dev/ref/settings/

There are some settings non standard  in django in the settings.py file,
quite self explanatory, but  you can ask us if you  need help with them.
See Contact seccion for that.

For example  all the  actions are  geolocalized based  on the  user's ip
address.  But in  order for  this  to work  you  need to  first have  to
download  the  geolocalized  cities  data  base and  put  it  where  the
settings.py will look it for:

```sh
$ cd agora_site/media/ && mkdir -p media/data && cd media/data
$ wget http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz
$ gunzip GeoLiteCity.dat.gz && rm GeoLiteCity.dat.gz
```


### Contribute

We would be  happy to consider any additions or  bugfixes that you would
like to add to the project. Please send them to us.

If you find  a bug or would like  to request a feature you may  do so at
the issue tracker for this project:

    [Issues](https://github.com/agoraciudadana/agora-ciudadana/issues/new)

Note that you don't  need to be a developer to be  able to contribute to
Agora: You can also help  us adding or maintaining translations, testing
the releases or improving the wiki. Don't hesitate to contact with us if
you want to help, your collaboration will be much appreciated.

We use Trello for managing the  work in the project, using the following
board where  all the  work we are  doing and planning  to do  for future
releases can be seen at a glance:

    [Trello](https://trello.com/board/agora-ciudadana/5054e9e060d5bc9a08196b96)


### Contact

Should  you have  any  doubt or  problem please  contact  us sending  an
email to agora-ciudadana-devel@googlegroups.com which is the development
mailing list of the project. The url of the google group is:

   [Agora Ciudadana Dev](https://groups.google.com/group/agora-ciudadana-devel)

That's all!

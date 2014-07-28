### Introduction

Agora Ciudadana is a social web site where anyone can create or join in an agora.
An agora has a set of members which can vote in the agora's elections either by
direct vote or by delegating the vote.

### Dependencies

Agora has only been tested to work in Linux-based servers so far.

* python
* virtualenvwrapper
* python2.7-dev
* rabbitmq-server
* git
* gettext

* You can install the dependencies by running the following command:

    Ubuntu/Debian: $ sudo apt-get install python2.7-dev python virtualenvwrapper rabbitmq-server git gettext

    openSUSE: # zypper in python python-virtualenvwrapper python-devel rabbitmq-server git gettext-tools

Other dependencies will be installed with virtualenv.

### First installation

Here we will detail the most simple way to get the application running. For a
more detailed explanation about how to deploy a django, refer to:
http://docs.djangoproject.com/en/dev/topics/install/

First we need to create the virtual environment where dependencies will be
installed:

    $ mkvirtualenv agora-ciudadana

Now everytime we want to use the installed virtualenv, we can do the
following:

    $ workon agora-ciudadana

Now we will install the dependencies:

    $ pip install -r requirements.txt --upgrade

After that, we need to configure the database (we use sqlite by default):

    $ ./manage.py syncdb --all

And mark all migration scripts as applied (because we have created the database
with --all option):

    $ ./manage.py migrate --fake

We use django haystack for searching, so we need to create the initial index:

    $ ./manage.py rebuild_index --noinput

Sometimes permissions are not created by django correctly. Running the following
command fixes this problem:

    $ ./manage.py check_permissions

We use celery and rabbitmq for programmed tasks, so you need to setup it correctly
in your server. Usually you just need to install it and run it as a system daemon
with:

    $ sudo /etc/rc.d/rabbitmq start

In some occasions, for example if you are using ubuntu or Opensuse, the command
above won't work. You need use this one instead:

    $ sudo service rabbitmq-server start

And then for celery to actually process the tasks sent to it (for example start
or stop an election), you need to run it as a daemon:

    $ ./manage.py celeryd -l INFO -B -S djcelery.schedulers.DatabaseScheduler

That's it! Start the webserver with:

    $ ./manage.py runserver

Now you'll be able to enter to Agora in http://localhost:8000

Of course this is a very simple and local installation. We recomend using a
web server like cherokee, lighthttpd or apache configured to use fast-cgi and
django, and a more powerful database like postgresql. Django documentation
explains how to do that:
http://docs.djangoproject.com/en/dev/topics/install/

We also refer to celery documentation for more details on how
to setup them correctly in your server:
http://docs.celeryproject.org/en/latest/getting-started/brokers/rabbitmq.html

### Translations

Agora Ciudadana has internationalization support and is translated to multiple
languages. In order to make these translations available in your installation,
you need to compile the translation (.po) files:

    $ ./manage.py compilemessages

### Production server

To deploy agora in a production server, you need do some changes. First, you
need to choose a web server: we have tested agora with apache, nginx and
cherokee.

You need to edit settings (custom_settings.py) and set DEBUG=False. You also
need to compile the javascript code into one single file, which is done for
optimization only for production:

    $ make dependencies && make all

### Making search work

Agora uses django-haystack with whoosh backend by default. This means that you
need to run ./manage.py update_index regularly to keep the search index updated.
You can do this in a nightly cron task, for example.

### Settings configuration

The settings.py file contains the default configuration for the project. You
shouldn't modify it; any settings configuration you need should be added to the
custom_settings.py file.

Most of the variables in settings are self-explanatory and are documented in
django: http://docs.djangoproject.com/en/dev/ref/settings/

There are some settings non standard in django in the settings.py file,
quite self explanatory, but you can ask us if you need help with them. See
Contact seccion for that.

For example all the actions are geolocalized based on the user's ip address. But
in order for this to work you need to first have to download the geolocalized
cities data base and put it where the settings.py will look it for:

    $ cd agora_site/ && mkdir -p media/data && cd media/data
    $ wget http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz
    $ gunzip GeoLiteCity.dat.gz

### FNMT configuration

TODO: needs more detailed instructions!

To allow FNMT login you'll have to configure your server properly. You'll have
to download the CA certificate from https://www.cert.fnmt.es/index.php?cha=cit&sec=4&page=139&lang=es
and then convert it to PEM format:

    $ openssl x509 -inform DER -in FNMTClase2CA.crt -text -fingerprint > ca.pem

### Contribute

We would be happy to consider any additions or bugfixes that you would like to
add to the project. Please send them to us.

If you find a bug or would like to request a feature you may do so at our
trello board:

https://trello.com/board/agora-ciudadana/5054e9e060d5bc9a08196b96

Note that you don't need to be a developer to be able to contribute to Agora:
You can also help us adding or maintaining translations, testing the releases,
improving the wiki, marketing the project. Just don't hesitate to contact
with us if you want to help, your collaboration will be much appreciated.

We use Trello for managing the work in the project, using the following board
where all the work we are doing and planning to do for future releases can be
seen at a glance:

https://trello.com/board/agora-ciudadana/5054e9e060d5bc9a08196b96

### Contact

Should you have any doubt or problem please contact us sending an email to
agora-ciudadana-devel@googlegroups.com which is the development mailing list of
the project. The url of the google group is:

https://groups.google.com/group/agora-ciudadana-devel


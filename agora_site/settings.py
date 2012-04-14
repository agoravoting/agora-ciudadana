# Django settings for votering project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Eduardo Robles Elvira', 'edulix@wadobo.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sqlite',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Madrid'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
#MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
#MEDIA_URL = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '_ntqq^5)ii^vd2o6cghis-@h8dy*4)-#()8q=yw*$!#^(8+(fd'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    'django.core.context_processors.request',
    "django.contrib.messages.context_processors.messages",
    'social_auth.context_processors.social_auth_by_name_backends',
    'agora_site.misc.context_processor.base',
    'agora_site.misc.context_processor.settings.SITE_NAME',
    'agora_site.misc.context_processor.settings.DEBUG',
    'agora_site.misc.context_processor.settings.MEDIA_URL',
)

ROOT_URLCONF = 'agora_site.urls'

import os
ROOT_PATH = os.path.dirname(__file__)
TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates'),
)

# Path for static docs (css, images, etc)
STATIC_DOC_ROOT = os.path.join(ROOT_PATH, 'site_media')

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(ROOT_PATH, 'static'),
)

# The list of finder backends that know how to find static files in various
# locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.comments',
    'django.contrib.staticfiles',
    'reversion',
    'south',
    'guardian',
    'easy_thumbnails',
    'userena',
    'rosetta',
    'actstream',
    'social_auth',
    'crispy_forms',
    'agora_site.agora_core',
    'agora_site.accounts',
    'endless_pagination',
)

# A list the models that you want to enable actions for. Models must be in the
# format app_label.model_name . In the background, django-activity-stream sets
# up GenericRelations to handle stream generation.
# More info: http://justquick.github.com/django-activity-stream/configuration.html

ACTSTREAM_ACTION_MODELS = [
    'auth.User',
    'agora_core.Agora',
    'agora_core.Election',
    'agora_core.CastVote',
]

# Modify the defaults to use BCrypt by default, because it's more secure, better
# for long term password storage
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
)

from django.contrib.messages import constants as message_constants
# This sets the mapping of message level to message tag, which is typically rendered as a CSS class in HTML
MESSAGE_TAGS = {
    message_constants.DEBUG: 'alert-info',
    message_constants.INFO: 'alert-info',
    message_constants.SUCCESS: 'alert-success',
    message_constants.WARNING: 'alert-warning',
    message_constants.ERROR: 'alert-error',
}

# Settings for endless pagination

ENDLESS_PAGINATION_PER_PAGE = 20

# Settings for django-social auth
AUTHENTICATION_BACKENDS = (
    'social_auth.backends.twitter.TwitterBackend',
    #'social_auth.backends.facebook.FacebookBackend',
    #'social_auth.backends.google.GoogleOAuthBackend',
    #'social_auth.backends.google.GoogleOAuth2Backend',
    #'social_auth.backends.google.GoogleBackend',
    #'social_auth.backends.yahoo.YahooBackend',
    #'social_auth.backends.browserid.BrowserIDBackend',
    #'social_auth.backends.contrib.linkedin.LinkedinBackend',
    #'social_auth.backends.contrib.livejournal.LiveJournalBackend',
    #'social_auth.backends.contrib.orkut.OrkutBackend',
    #'social_auth.backends.contrib.foursquare.FoursquareBackend',
    #'social_auth.backends.contrib.github.GithubBackend',
    #'social_auth.backends.contrib.dropbox.DropboxBackend',
    #'social_auth.backends.contrib.flickr.FlickrBackend',
    #'social_auth.backends.contrib.instagram.InstagramBackend',
    #'social_auth.backends.OpenIDBackend',
    'userena.backends.UserenaAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
)

TWITTER_CONSUMER_KEY         = ''
TWITTER_CONSUMER_SECRET      = ''

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/signin/'
LOGOUT_URL = '/accounts/signout/'
LOGIN_ERROR_URL    = '/accounts/signin/'

# Django crispy forms settings

CRISPY_FAIL_SILENTLY = not DEBUG

# userena settings

# For debugging, use the dummy backend, else comment this and django will use
# the smtp as by default
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

USERENA_SIGNIN_REDIRECT_URL = '/'

USERENA_REDIRECT_ON_SIGNOUT = '/'

USERENA_ACTIVATION_REQUIRED = True

USERENA_FORBIDDEN_USERNAMES = (
    'signup', 'signout', 'signin', 'activate', 'me', 'password', 'admin',
    'agora', 'staff', 'agoraciudadana', 'agoravoting'
)

USERENA_MUGSHOT_SIZE = 50

USERENA_WITHOUT_USERNAMES = True

# required by  django-guardian to be set
ANONYMOUS_USER_ID = -1

# Project settings

SITE_NAME = 'Agora Ciudadana'

AUTH_PROFILE_MODULE = 'agora_core.Profile'


try:
    # custom settings is the file where you should set your modifications of the
    # settings file
    from custom_settings import *
except:
    pass

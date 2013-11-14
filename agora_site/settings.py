from django.utils.translation import ugettext_lazy as _

DEBUG = True
TEMPLATE_DEBUG = DEBUG


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


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

USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

LANGUAGES = (
    ('es', _('Spanish')),
    ('en', _('English')),
    ('gl', _('Galician')),
    ('eu', _('Basque')),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Make this unique, and don't share it with anybody.
SECRET_KEY = '_ntqq^5)ii^vd2o6cghis-@h8dy*4)-#()8q=yw*$!#^(8+(fd'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_auth.middleware.SocialAuthExceptionMiddleware',
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
    'agora_site.misc.context_processor.settings.AUTHENTICATION_BACKENDS',
    'agora_site.misc.context_processor.settings.AGORA_FNMT_BASE_URL',
)

ROOT_URLCONF = 'agora_site.urls'

import os
ROOT_PATH = os.path.dirname(__file__)
TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates'),
)


# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(ROOT_PATH, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

LOCALE_PATHS = (
    os.path.join(ROOT_PATH, 'locale'),
    os.path.join(os.path.dirname(ROOT_PATH), 'userena', 'locale'),
)

# IP database geolocalization:
# You can download it from http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz
# and uncompress it with gunzip GeoLiteCity.dat.gz
GEOIP_DB_PATH = os.path.join(ROOT_PATH, 'media', 'data', 'GeoLiteCity.dat')

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
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.messages',
    # WARNING! you should disable admin in production sites for security:
    #'django.contrib.admin',
    'django.contrib.comments',
    'django.contrib.markup',
    'django.contrib.flatpages',
    'debug_toolbar',
    'south',
    'tastypie',
    'easy_thumbnails',
    'userena',
    'rosetta',
    'actstream',
    'social_auth',
    'crispy_forms',
    'agora_site.agora_core',
    'agora_site.accounts',
    'haystack',
    'captcha',
    'djcelery',
    'guardian',
    'djsgettext'
)

# Cache settings

# No caching by default for development
#if DEBUG:
    #CACHES = {
        #'default': {
            #'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        #}
    #}

# A list the models that you want to enable actions for. Models must be in the
# format app_label.model_name . In the background, django-activity-stream sets
# up GenericRelations to handle stream generation.
# More info: http://justquick.github.com/django-activity-stream/configuration.html

ACTSTREAM_ACTION_MODELS = [
    'auth.User',
    'agora_core.Agora',
    'agora_core.Election',
    'agora_core.CastVote',
    'comments.Comment'
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

SUCCESS_MODAL = 27
MESSAGE_TAGS = {
    message_constants.DEBUG: 'alert-info',
    message_constants.INFO: 'alert-info',
    message_constants.SUCCESS: 'alert-success',
    SUCCESS_MODAL: 'alert-success-modal',
    message_constants.WARNING: 'alert-warning',
    message_constants.ERROR: 'alert-error',
}

# Settings for endless pagination

ENDLESS_PAGINATION_PER_PAGE = 20

# Settings for django-social auth
AUTHENTICATION_BACKENDS = (
    #'agora_site.agora_core.backends.fnmt.FNMTBackend',
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
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

SOCIAL_AUTH_RAISE_EXCEPTIONS = False
SOCIAL_AUTH_SLUGIFY_USERNAMES = True
SOCIAL_AUTH_UUID_LENGTH = 2

TWITTER_CONSUMER_KEY         = ''
TWITTER_CONSUMER_SECRET      = ''

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/signin/'
LOGOUT_URL = '/accounts/signout/'
LOGIN_ERROR_URL    = '/accounts/signin/'

# Django crispy forms settings

CRISPY_FAIL_SILENTLY = not DEBUG

CRISPY_TEMPLATE_PACK = 'bootstrap'

# Haystack

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(ROOT_PATH, 'whoosh_index'),
    },
}

# userena settings

# For debugging, use the dummy backend, else comment this and django will use
# the smtp as by default
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = 'noreply@localhost'

USERENA_SIGNIN_REDIRECT_URL = '/'

USERENA_REDIRECT_ON_SIGNOUT = '/'

USERENA_ACTIVATION_REQUIRED = True

USERENA_FORBIDDEN_USERNAMES = (
    'signup', 'signout', 'signin', 'activate', 'me', 'password', 'admin',
    'agora', 'staff', 'agoraciudadana', 'agoravoting', 'root', 'administrator',
    'adminstrador', 'hostmaster', 'info', 'ssladmin', 'sysadmin', 'webmaster',
    'no-reply', 'mail', 'email', 'accounts', 'misc', 'api', 'search',
    'settings', 'edit', 'list', 'login'
)

USERENA_MUGSHOT_SIZE = 50
MUGSHOTS_DIR = "mugshots/"
USERENA_MUGSHOT_PATH =  os.path.join(MEDIA_ROOT, MUGSHOTS_DIR)

USERENA_WITHOUT_USERNAMES = False

USERENA_MUGSHOT_DEFAULT = "blank-unitials-ssl"

# required by  django-guardian to be set
ANONYMOUS_USER_ID = -1

# Celery settings

import djcelery
djcelery.setup_loader()

BROKER_URL = 'amqp://guest:guest@localhost:5672/'
CELERY_RESULT_BACKEND = "amqp://guest:guest@localhost:5672/"
CELERY_DISABLE_RATE_LIMITS = True

from celery.schedules import crontab
CELERYBEAT_SCHEDULE = {
    # Executes clean_expired_users task every day at 7:30 A.M
    'every-monday-morning': {
        'task': 'agora_site.agora_core.tasks.election.clean_expired_users',
        'schedule': crontab(hour=7, minute=30),
    },
}

# Rosetta settings
ROSETTA_ENABLE_TRANSLATION_SUGGESTIONS = True

# Django debug toolbar settings

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

# Project settings

SITE_NAME = 'Agora Ciudadana'

AUTH_PROFILE_MODULE = 'agora_core.Profile'

INTERNAL_IPS = ('127.0.0.1',)

# This settings allows to configure who can create agoras. For the users who
# cannot create agoras, the Create Agora button won't appear. Possible values
# are:
#  * "any-user" (default) - Any logged in user can create agoras. Anonymous
#    users will also see the button but they will be redirected to the login
#    pagewhen they click on it.
#  * "superusers-only" - Only users whose is_superuser() function returns true
#    will see the create agora button and will be able to create agoras.
AGORA_CREATION_PERMISSIONS="any-user"

# List of agoras to which a user will be joined automatically when they are
# registered
AGORA_REGISTER_AUTO_JOIN = []

# Active voting methods in this deployment
VOTING_METHODS = (
    'agora_site.agora_core.models.voting_systems.plurality.Plurality',
    'agora_site.agora_core.models.voting_systems.meek_stv.MeekSTV',
)

AGORA_USE_HTTPS = False

USE_ESI = False

# This indicates if the user is allowed to use FNMT certificates as a login or
# authentication method. Disabled by default because this is a spanish thingie.
#
# See INSTALL.md for more details
AGORA_ALLOW_FNMT_CERTIFICATE = False

# Allow users registered via the API to be activated with a link
AGORA_ALLOW_API_AUTO_ACTIVATION = False

# the API caller will have to provide this secret to be able to do API
# auto-activation
AGORA_API_AUTO_ACTIVATION_SECRET = 'change the activation secret'

AGORA_FNMT_BASE_URL = "https://fnmt.local.dev"
AGORA_BASE_URL = "https://local.dev"

# sets default value for max age in cache.
# set to zero (no-cache) by default
CACHE_MIDDLEWARE_SECONDS = 0

# sets the max age for calls that do not need to be very updated
# set to zero (no-cache) by default
MANY_CACHE_SECONDS = 0

# sets the max age for calls that need to be very updated
# set to zero (no-cache) by default
FEW_CACHE_SECONDS = 0

# Stablishes how many failed login attempts for a given user are allowed before
# a captcha is shown
MAX_ALLOWED_FAILED_LOGIN_ATTEMPTS = 5

ALLOWED_HOSTS = [
    '.local.dev',
]

try:
    # custom settings is the file where you should set your modifications of the
    # settings file
    from custom_settings import *
except:
    pass

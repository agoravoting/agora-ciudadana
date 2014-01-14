from agora_site.settings import *

SOUTH_TESTS_MIGRATE = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'testdb.sqlite',                # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# remove django secure to make tests work
MIDDLEWARE_CLASSES = tuple([
    i for i in MIDDLEWARE_CLASSES
        if i != 'djangosecure.middleware.SecurityMiddleware'])

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(ROOT_PATH, 'whoosh_test_index'),
    },
}

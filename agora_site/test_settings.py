from agora_site.settings import *

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(ROOT_PATH, 'whoosh_test_index'),
    },
}

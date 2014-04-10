from django.utils.translation import ugettext_lazy as _

AGORA_REGISTER_EXTRA_FIELDS = [
    {
        'field_name': "nie",
        'label': _('DNI/NIE'),
        'position': 3,
        'help_text': _('Especify your DNI or NIE. Examples: 12345678Y, Y2345678A'),
        'validator': "agora_site.multireferendum_validators.nie_validator"
    },
    {
        'field_name': "postal_code",
        'label': _('Postal Code'),
        'position': 4,
        'help_text': _('Example: 11130'),
        'validator': "agora_site.multireferendum_validators.postal_code_val"
    }
]

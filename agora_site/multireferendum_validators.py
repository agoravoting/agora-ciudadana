from django.utils.translation import ugettext_lazy as _
from django import forms
import re

CP_RX = re.compile('^[0-9]{4,5}$')

NIE_RX = re.compile("^[A-Z]?[0-9]{7,8}[A-Z]$", re.IGNORECASE)
LETTER_RX = re.compile("^[A-Z]$", re.IGNORECASE)

def nie_validator(value):
    if not isinstance(value, basestring):
        raise forms.ValidationError(_('Invalid DNI/NIE.'))

    val2 = value.upper()
    if not NIE_RX.match(val2):
        raise forms.ValidationError(_('Invalid DNI/NIE.'))

    if LETTER_RX.match(val2[0]):
        nie_letter = val2[0]
        val2 = val2[1:]
        if nie_letter == 'Y':
            val2 = "1" + val2
        elif nie_letter == 'Z':
            val2 = "2" + val2

    mod_letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    digits = val2[:-1]
    letter = val2[-1].upper()

    expected = mod_letters[int(digits) % 23]

    if letter != expected:
        raise forms.ValidationError(_('Invalid DNI/NIE letter.'))

def postal_code_val(value):
    if not CP_RX.match(value):
        raise forms.ValidationError(_('Invalid postal code (must be a number).'))
    return value

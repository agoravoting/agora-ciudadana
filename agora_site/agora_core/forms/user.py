from django import forms as django_forms
from django.contrib.auth.models import User

from agora_site.misc.utils import FormRequestMixin

class UsernameAvailableForm(django_forms.Form, FormRequestMixin):
    def __init__(self, *args, **kwargs):
        super(UsernameAvailableForm, self).__init__(*args, **kwargs)

    def is_valid(self):
        return User.objects.filter(username=self.data["username"]).count() == 0

    class Meta:
        model = User
        fields = ('username')

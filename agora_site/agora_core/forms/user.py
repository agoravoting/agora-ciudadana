from django import forms as django_forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from userena import settings as userena_settings
from userena import forms as userena_forms
from agora_site.misc.utils import FormRequestMixin

class UsernameAvailableForm(django_forms.Form, FormRequestMixin):
    def __init__(self, *args, **kwargs):
        super(UsernameAvailableForm, self).__init__(*args, **kwargs)

    def is_valid(self):
        return User.objects.filter(username=self.data["username"]).count() == 0

    class Meta:
        model = User
        fields = ('username')

class LoginForm(userena_forms.AuthenticationForm):
    def is_valid(self):
        if super(LoginForm, self).is_valid():
            identification, password, remember_me = (self.cleaned_data['identification'],
                self.cleaned_data['password'], self.cleaned_data['remember_me'])
            user = authenticate(identification=identification, password=password)
            if user.is_active:
                login(self.request, user)
                if remember_me:
                    self.request.session.set_expiry(userena_settings.USERENA_REMEMBER_ME_DAYS[1] * 86400)
                else:
                    self.request.session.set_expiry(0)
                return True
            else:
                return False
        else:
            return False
from django import forms as django_forms
from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils import translation, timezone
from django.contrib.markup.templatetags.markup import textile
from django.utils.translation import gettext as _
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404

from userena import settings as userena_settings
from userena import forms as userena_forms

from agora_site.misc.utils import FormRequestMixin
from agora_site.agora_core.forms.comment import COMMENT_MAX_LENGTH
from agora_site.misc.utils import send_mass_html_mail, get_base_email_context

class UsernameAvailableForm(django_forms.Form, FormRequestMixin):
    def __init__(self, *args, **kwargs):
        super(UsernameAvailableForm, self).__init__(*args, **kwargs)

    def is_valid(self):
        return User.objects.filter(username=self.data["username"]).count() == 0

    class Meta:
        model = User
        fields = ('username')

class LoginForm(userena_forms.AuthenticationForm):
    def __init__(self, request, data):
        self.request = request
        return super(LoginForm, self).__init__(data=data)

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

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        return dict(request=request, data=data)

class SendMailForm(django_forms.Form):
    '''
    Base comment. This is inherited by others
    '''
    comment = django_forms.CharField(label='', max_length=COMMENT_MAX_LENGTH)

    def __init__(self, request, target_user, *args, **kwargs):
        super(SendMailForm, self).__init__(*args, **kwargs)
        self.request = request
        self.target_user = target_user

    def save(self):
        translation.activate(self.target_user.get_profile().lang_code)
        context = get_base_email_context(self.request)
        context['to'] = self.target_user
        context['from'] = self.request.user
        context['comment'] = self.cleaned_data['comment']
        datatuples= [(
            _('Message from %s') % self.request.user.get_profile().get_fullname(),
            render_to_string('agora_core/emails/user_mail.txt',
                context),
            render_to_string('agora_core/emails/user_mail.html',
                context),
            None,
            [self.target_user.email])
        ]

        translation.deactivate()

        send_mass_html_mail(datatuples)

        return None

    def clean_comment(self):
        """
        If COMMENTS_ALLOW_PROFANITIES is False, check that the comment doesn't
        contain anything in PROFANITIES_LIST.
        """

        if not self.request.user.is_authenticated():
            raise django_forms.ValidationError(ungettext("You must be authenticated to post a comment"))

        comment = self.cleaned_data["comment"]
        if settings.COMMENTS_ALLOW_PROFANITIES == False:
            bad_words = [w for w in settings.PROFANITIES_LIST if w in comment.lower()]
            if bad_words:
                plural = len(bad_words) > 1
                raise django_forms.ValidationError(ungettext(
                    "Watch your mouth! The word %s is not allowed here.",
                    "Watch your mouth! The words %s are not allowed here.", plural) % \
                    get_text_list(['"%s%s%s"' % (i[0], '-'*(len(i)-2), i[-1]) for i in bad_words], 'and'))

        return comment

    @staticmethod
    def static_get_form_kwargs(request, data, *args, **kwargs):
        '''
        Returns the parameters that will be sent to the constructor
        '''
        ret_kwargs = dict(
            request=request,
            data=data
        )

        ret_kwargs['target_user'] = get_object_or_404(User, pk=kwargs["userid"])
        return ret_kwargs
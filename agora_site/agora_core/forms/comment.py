
import datetime
import json

from django import forms as django_forms
from django.contrib.comments.forms import CommentSecurityForm
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _, ungettext
from django.utils import timezone

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from actstream.models import Action
from actstream.signals import action

from agora_site.agora_core.models import Agora, Election, Profile
from agora_site.misc.utils import geolocate_ip

COMMENT_MAX_LENGTH = getattr(settings, 'COMMENT_MAX_LENGTH', 3000)


class PostCommentForm(django_forms.Form):
    '''
    Base comment. This is inherited by others
    '''
    comment = django_forms.CharField(label='', max_length=COMMENT_MAX_LENGTH,
        widget=django_forms.Textarea(
            attrs=dict(placeholder=_('Post a comment here...'))))

    def __init__(self, request, target_object, *args, **kwargs):
        # removing instance from kwargs because it isn't a ModelForm
        kwargs.pop("instance", None)
        super(PostCommentForm, self).__init__(*args, **kwargs)
        self.request = request
        self.target_object = target_object

        self.helper = FormHelper()
        self.helper.form_id = "post-comment"
        self.helper.form_class = "form-inline"
        self.helper.add_input(Submit('submit', _('Send'), css_class='btn btn-success btn-large'))

    def save(self):
        obj = self.get_comment_object()
        obj.save()

        action.send(self.request.user, verb='commented', target=self.target_object,
            action_object=obj, ipaddr=self.request.META.get('REMOTE_ADDR'),
            geolocation=json.dumps(geolocate_ip(self.request.META.get('REMOTE_ADDR'))))

        return obj

    def get_comment_object(self):
        """
        Return a new (unsaved) comment object based on the information in this
        form. Assumes that the form is already validated and will throw a
        ValueError if not.

        Does not set any of the fields that would come from a Request object
        (i.e. ``user`` or ``ip_address``).
        """
        if not self.is_valid():
            raise ValueError("get_comment_object may only be called on valid forms")

        CommentModel = self.get_comment_model()
        new = CommentModel(**self.get_comment_create_data())
        new = self.check_for_duplicate_comment(new)

        return new

    def get_comment_model(self):
        """
        Get the comment model to create with this form. Subclasses in custom
        comment apps should override this, get_comment_create_data, and perhaps
        check_for_duplicate_comment to provide custom comment models.
        """
        return Comment

    def get_comment_create_data(self):
        return dict(
            content_type = ContentType.objects.get_for_model(self.target_object),
            object_pk    = force_unicode(self.target_object._get_pk_val()),
            user         = self.request.user,
            comment      = self.cleaned_data["comment"],
            submit_date  = timezone.now(),
            site_id      = settings.SITE_ID,
            is_public    = True,
            is_removed   = False,
        )

    def check_for_duplicate_comment(self, new):
        """
        Check that a submitted comment isn't a duplicate. This might be caused
        by someone posting a comment twice. If it is a dup, silently return the *previous* comment.
        """
        possible_duplicates = self.get_comment_model()._default_manager.using(
            self.target_object._state.db
        ).filter(
            content_type = new.content_type,
            object_pk = new.object_pk,
            user = new.user,
        )
        for old in possible_duplicates:
            if old.submit_date.date() == new.submit_date.date() and old.comment == new.comment:
                return old

        return new

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

        if 'user' in kwargs:
            ret_kwargs['target_object'] = User.objects.get(username=kwargs["user"])
        elif 'agora' in kwargs:
            ret_kwargs['target_object'] = Agora.objects.get(pk=kwargs["agora"])
        elif 'election' in kwargs:
            ret_kwargs['target_object'] = Election.objects.get(pk=kwargs["election"])

        return ret_kwargs

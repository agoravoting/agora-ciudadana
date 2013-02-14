
from agora_site.agora_core.models import Agora, Election, Profile, CastVote
from agora_site.misc.utils import *
from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora

from actstream.signals import action

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils import translation
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from celery import task

import datetime

@task(ignore_result=True)
def send_request_membership_mails(agora_id, user_id, is_secure, site_id, remote_addr):
    user = User.objects.get(pk=user_id)
    agora = Agora.objects.get(pk=agora_id)

    # Mail to the admins
    context = get_base_email_context_task(is_secure, site_id)
    context.update(dict(
        agora=agora,
        other_user=user,
        notification_text=_('%(username)s has requested membership at '
            '%(agora)s. Please review this pending request') % dict(
                username=user.username,
                agora=agora.get_full_name()
            ),
        extra_urls=(
            (_('Accept membership request'),
            reverse('agora-action-accept-membership-request',
                kwargs=dict(
                    username=agora.creator,
                    agoraname=agora.name,
                    username2=user.username
                ))
            ),
            (_('Dismiss membership request'),
            reverse('agora-action-dismiss-membership-request',
                kwargs=dict(
                    username=agora.creator,
                    agoraname=agora.name,
                    username2=user.username
                ))
            )
        ),
    ))
    for admin in agora.admins.all():
        translation.activate(admin.get_profile().lang_code)

        if not admin.get_profile().has_perms('receive_email_updates'):
            continue

        context['to'] = admin

        email = EmailMultiAlternatives(
            subject=_('%(site)s - New membership request at %(agora)s') %\
                dict(
                    site=Site.objects.get_current().domain,
                    agora=agora.get_full_name()
                ),
            body=render_to_string('agora_core/emails/agora_notification.txt',
                context),
            to=[admin.email])

        email.attach_alternative(
            render_to_string('agora_core/emails/agora_notification.html',
                context), "text/html")
        email.send()

    translation.deactivate()

@task(ignore_result=True)
def send_request_admin_membership_mails(agora_id, user_id, is_secure, site_id, remote_addr):
    user = User.objects.get(pk=user_id)
    agora = Agora.objects.get(pk=agora_id)

    # Mail to the admins
    context = get_base_email_context_task(is_secure, site_id)
    context.update(dict(
        agora=agora,
        other_user=user,
        notification_text=_('%(username)s has requested admin membership at '
            '%(agora)s. Please review this pending request') % dict(
                username=user.username,
                agora=agora.get_full_name()
            ),
        extra_urls=(
            (_('Accept admin membership request'),
            reverse('agora-action-admin-accept-membership-request',
                kwargs=dict(
                    username=agora.creator,
                    agoraname=agora.name,
                    username2=user.username
                ))
            ),
            (_('Dismiss membership request'),
            reverse('agora-action-dismiss-admin-membership-request',
                kwargs=dict(
                    username=agora.creator,
                    agoraname=agora.name,
                    username2=user.username
                ))
            )
        ),
    ))
    for admin in agora.admins.all():
        translation.activate(admin.get_profile().lang_code)

        if not admin.get_profile().has_perms('receive_email_updates'):
            continue

        context['to'] = admin

        email = EmailMultiAlternatives(
            subject=_('%(site)s - New admin membership request at %(agora)s') %\
                dict(
                    site=Site.objects.get_current().domain,
                    agora=agora.get_full_name()
                ),
            body=render_to_string('agora_core/emails/agora_notification.txt',
                context),
            to=[admin.email])

        email.attach_alternative(
            render_to_string('agora_core/emails/agora_notification.html',
                context), "text/html")
        email.send()

    translation.deactivate()

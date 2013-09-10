
from agora_site.agora_core.models import Agora, Election, Profile, CastVote
from agora_site.misc.utils import *
from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora
from agora_site.agora_core.templatetags.string_tags import urlify_markdown

from actstream.signals import action

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils import translation
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from celery import task

import markdown
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
            (_('List of membership requests'),
            reverse('agora-members',
                kwargs=dict(
                    username=agora.creator,
                    agoraname=agora.name,
                    members_filter="membership_requests"
                ))
            ),
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
            (_('List of admin membership requests'),
            reverse('agora-members',
                kwargs=dict(
                    username=agora.creator,
                    agoraname=agora.name,
                    members_filter="admin_membership_requests"
                ))
            ),
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

@task(ignore_result=True)
def send_mail_to_members(agora_id, user_id, is_secure, site_id, remote_addr,
        receivers, subject, body):
    sender = User.objects.get(pk=user_id)
    agora = Agora.objects.get(pk=agora_id)

    if receivers == 'members':
        receivers = agora.members.all()
    elif receivers == 'admins':
        receivers = agora.admins.all()
    elif receivers == 'delegates':
        receivers = agora.active_delegates()
    elif receivers == 'non-delegates':
        receivers = agora.non_delegates()
    elif receivers == 'non-voters':
        receivers = agora.non_voters()
    elif receivers == 'requested-membership':
        receivers = agora.users_who_requested_membership()

    # Mail to the admins
    context = get_base_email_context_task(is_secure, site_id)
    context.update(dict(
        agora=agora,
        other_user=sender,
        notification_text=body
    ))
    context_html = context.copy()
    context_html["notification_text"] = markdown.markdown(urlify_markdown(body))

    for receiver in receivers:
        if not receiver.get_profile().has_perms('receive_email_updates'):
            continue

        translation.activate(receiver.get_profile().lang_code)
        context['to'] = receiver

        email = EmailMultiAlternatives(
            subject=subject,
            body=render_to_string('agora_core/emails/agora_notification.txt',
                context),
            to=[receiver.email])

        email.attach_alternative(
            render_to_string('agora_core/emails/agora_notification.html',
                context_html), "text/html")
        email.send()

    translation.deactivate()
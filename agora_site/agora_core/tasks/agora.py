
from agora_site.agora_core.models import Agora, Election, Profile, CastVote
from agora_site.misc.utils import *
from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora
from agora_site.agora_core.templatetags.string_tags import urlify_markdown

from actstream.signals import action

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.translation import ugettext_lazy as _
from django.utils import translation
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from celery import task
from celery.contrib import rdb

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

    base_tmpl = 'agora_core/emails/agora_notification'

    extra_notification_text_generator = None
    context = get_base_email_context_task(is_secure, site_id)

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
        base_tmpl = 'agora_core/emails/non_voters'

        def text_gen(user):
            token = default_token_generator.make_token(user)
            login_url = reverse('auto-login-token',
                    kwargs=dict(username=user, token=token))

            return _("\nHere we provide you a custom link so you can directly "
                "access the election:\n%(protocol)s://%(domain)s%(url)s") % dict(
                protocol=context['protocol'],
                domain=context['site'].domain,
                url=login_url
            ), _("<p>Here we provide you a custom link so you can directly access the election:</p>\n<a href=\"%(protocol)s://%(domain)s%(url)s\">%(protocol)s://%(domain)s%(url)s</a><br/>") % dict(
                protocol=context['protocol'],
                domain=context['site'].domain,
                url=login_url
            )

        extra_notification_text_generator = text_gen

    elif receivers == 'requested-membership':
        receivers = agora.users_who_requested_membership()
    elif receivers == 'unconfirmed-open-votes':
        election = agora.get_featured_election()
        if not election or not election.has_started() or election.has_ended():
            return

        receivers = []
        def text_gen(user):
            token = default_token_generator.make_token(user)
            confirm_vote_url = reverse('confirm-vote-token',
                    kwargs=dict(username=user, token=token))

            return _("You have a vote pending from confirmation. If you really emitted this vote, please confirm this vote click the following confirmation url:\n %(protocol)s://%(domain)s%(url)s\n") % dict(
                protocol=context['protocol'],
                domain=context['site'].domain,
                url=confirm_vote_url
            ), _("<p>You have a vote pending from confirmation. If you really emitted this vote, please confirm this vote click the following confirmation url:</p>\n<a href=\"%(protocol)s://%(domain)s%(url)s\">%(protocol)s://%(domain)s%(url)s</a><br/>") % dict(
                protocol=context['protocol'],
                domain=context['site'].domain,
                url=confirm_vote_url
            )

        extra_notification_text_generator = text_gen
        for v in CastVote.objects.filter(election__id=election.id,
            is_counted=False):
            if  CastVote.objects.filter(election__id=election.id, is_counted=False, voter__id=v.voter.id).count() > 0 and v.voter not in receivers and v.voter.is_active and election.has_perms("vote_counts", v.voter) and isinstance(v.voter.get_profile().extra, dict) and "pending_ballot_id" in v.voter.get_profile().extra:
                pbi = v.voter.get_profile().extra.get('pending_ballot_id')
                if v.voter.get_profile().extra.get('pending_ballot_status_%d' % pbi) != 'confirmed':
                    receivers.append(v.voter)

    # Mail to the admins
    context.update(dict(
        agora=agora,
        other_user=sender,
        notification_text=body
    ))
    context_html = context.copy()
    context_html["notification_text"] = markdown.markdown(urlify_markdown(body))
    notification_text_base = context["notification_text"]
    notification_text_base_html_base = context_html["notification_text"]

    for receiver in receivers:
        if not receiver.get_profile().has_perms('receive_email_updates'):
            continue

        lang_code = receiver.get_profile().lang_code
        print "lang_code = ", lang_code
        if not lang_code:
            lang_code = settings.LANGUAGE_CODE
        print "lang_code = ", lang_code

        translation.activate(lang_code)
        context['to'] = receiver
        context_html['to'] = receiver

        if extra_notification_text_generator is not None:
            extra_text, extra_html = extra_notification_text_generator(receiver)
            context["notification_text"] = notification_text_base + "\n" + extra_text
            context_html["notification_text"] = notification_text_base_html_base + "<br/>\n" + extra_html

        email = EmailMultiAlternatives(
            subject=subject,
            body=render_to_string(base_tmpl + '.txt',
                context),
            to=[receiver.email])

        email.attach_alternative(
            render_to_string(base_tmpl + '.html',
                context_html), "text/html")
        email.send()

    translation.deactivate()

from agora_site.agora_core.models import Agora, Election, Profile, CastVote
from agora_site.misc.utils import *
from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora

from actstream.signals import action

from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.utils import translation, timezone
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from celery import task

import datetime


@task(ignore_result=True)
def start_election(election_id, is_secure, site_id, remote_addr, user_id):
    election = Election.objects.get(pk=election_id)
    if not election.is_approved or election.is_archived():
        election.voting_starts_at_date = None
        election.voting_ends_at_date = None
        election.voting_extended_until_date = None
        election.save()
        return

    if election.extra_data and "started" in election.extra_data:
        return

    if not election.voting_starts_at_date or\
            election.voting_starts_at_date > timezone.now():
        return

    election.voting_starts_at_date = timezone.now()
    if election.frozen_at_date is None:
        election.frozen_at_date = election.voting_starts_at_date
    election.create_hash()
    if not election.extra_data:
        election.extra_data = dict(started=True)
    else:
        election.extra_data["started"]=True
    election.save()

    context = get_base_email_context_task(is_secure, site_id)

    context.update(dict(
        election=election,
        election_url=reverse('election-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name, electionname=election.name)),
        agora_url=reverse('agora-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name)),
    ))

    # List of emails to send. tuples are of format:
    #
    # (subject, text, html, from_email, recipient)
    datatuples = []

    # NOTE: for now, electorate is dynamic and just taken from the election's
    # agora members' list
    for voter in election.agora.members.all():

        if not voter.get_profile().has_perms('receive_email_updates'):
            continue

        translation.activate(voter.get_profile().lang_code)
        context['to'] = voter
        context['allow_delegation'] = (election.agora.delegation_policy == Agora.DELEGATION_TYPE[0][0])
        try:
            context['delegate'] = get_delegate_in_agora(voter, election.agora)
        except:
            pass
        datatuples.append((
            _('Vote in election %s') % election.pretty_name,
            render_to_string('agora_core/emails/election_started.txt',
                context),
            render_to_string('agora_core/emails/election_started.html',
                context),
            None,
            [voter.email]))

    # Also notify third party delegates
    for voter in election.agora.active_nonmembers_delegates():

        if not voter.get_profile().has_perms('receive_email_updates'):
            continue

        translation.activate(voter.get_profile().lang_code)
        context['to'] = voter
        datatuples.append((
            _('Vote in election %s') % election.pretty_name,
            render_to_string('agora_core/emails/election_started.txt',
                context),
            render_to_string('agora_core/emails/election_started.html',
                context),
            None,
            [voter.email]))

    translation.deactivate()

    send_mass_html_mail(datatuples)

    user = User.objects.get(pk=user_id)

    action.send(user, verb='started voting period', action_object=election,
        target=election.agora, ipaddr=remote_addr,
        geolocation=json.dumps(geolocate_ip(remote_addr)))


@task(ignore_result=True)
def end_election(election_id, is_secure, site_id, remote_addr, user_id):
    election = Election.objects.get(pk=election_id)
    if not election.is_approved or election.is_archived():
        election.voting_extended_until_date = election.voting_ends_at_date = None
        election.save()
        return

    if election.extra_data and "ended" in election.extra_data:
        return

    if not election.voting_extended_until_date or not election.frozen_at_date or\
        election.voting_extended_until_date > timezone.now():
        return

    user = User.objects.get(pk=user_id)

    election.voting_extended_until_date = timezone.now()
    if not election.extra_data:
        election.extra_data = dict(ended=True)
    else:
        election.extra_data["ended"]=True
    election.save()
    election.compute_result()

@task(ignore_result=True)
def send_election_results(election_id, is_secure, site_id, remote_addr, user_id):
    election = Election.objects.get(pk=election_id)

    user = User.objects.get(pk=user_id)

    context = get_base_email_context_task(is_secure, site_id)

    context.update(dict(
        election=election,
        election_url=reverse('election-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name, electionname=election.name)),
        agora_url=reverse('agora-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name)),
    ))

    # List of emails to send. tuples are of format:
    #
    # (subject, text, html, from_email, recipient)
    datatuples = []

    for vote in election.get_all_votes():

        if not vote.voter.get_profile().has_perms('receive_email_updates'):
            continue

        translation.activate(vote.voter.get_profile().lang_code)
        context['to'] = vote.voter
        try:
            context['delegate'] = get_delegate_in_agora(vote.voter, election.agora)
        except:
            pass
        datatuples.append((
            _('Election results for %s') % election.pretty_name,
            render_to_string('agora_core/emails/election_results.txt',
                context),
            render_to_string('agora_core/emails/election_results.html',
                context),
            None,
            [vote.voter.email]))

    translation.deactivate()

    send_mass_html_mail(datatuples)

    action.send(user, verb='published results', action_object=election,
        target=election.agora, ipaddr=remote_addr,
        geolocation=json.dumps(geolocate_ip(remote_addr)))


@task(ignore_result=True)
def archive_election(election_id, is_secure, site_id, remote_addr, user_id):
    election = Election.objects.get(pk=election_id)
    if not election.is_archived():
        return

    context = get_base_email_context_task(is_secure, site_id)

    context.update(dict(
        election=election,
        election_url=reverse('election-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name, electionname=election.name)),
        agora_url=reverse('agora-view',
            kwargs=dict(username=election.agora.creator.username,
                agoraname=election.agora.name)),
    ))

    # List of emails to send. tuples are of format:
    #
    # (subject, text, html, from_email, recipient)
    datatuples = []

    for vote in election.get_all_votes():

        if not vote.voter.get_profile().has_perms('receive_email_updates'):
            continue

        translation.activate(vote.voter.get_profile().lang_code)
        context['to'] = vote.voter
        datatuples.append((
            _('Election results for %s') % election.pretty_name,
            render_to_string('agora_core/emails/election_archived.txt',
                context),
            render_to_string('agora_core/emails/election_archived.html',
                context),
            None,
            [vote.voter.email]))

    translation.deactivate()

    send_mass_html_mail(datatuples)

    action.send(user, verb='archived', action_object=election,
        target=election.agora, ipaddr=remote_addr,
        geolocation=json.dumps(geolocate_ip(remote_addr)))


@task(ignore_result=True)
def send_election_created_mails(election_id, is_secure, site_id, remote_addr, user_id):
    election = Election.objects.get(pk=election_id)
    if not election or election.is_archived():
        return

    context = get_base_email_context_task(is_secure, site_id)
    context.update(dict(
        election=election,
        action_user_url='/%s' % election.creator.username,
    ))

    # List of emails to send. tuples are of format:
    #
    # (subject, text, html, from_email, recipient)
    datatuples = []

    for admin in election.agora.admins.all():

        if not admin.get_profile().has_perms('receive_email_updates'):
            continue

        translation.activate(admin.get_profile().lang_code)
        context['to'] = admin
        datatuples.append((
            _('Election %s created') % election.pretty_name,
            render_to_string('agora_core/emails/election_created.txt',
                context),
            render_to_string('agora_core/emails/election_created.html',
                context),
            None,
            [admin.email]))

    translation.deactivate()

    send_mass_html_mail(datatuples)



@task(ignore_result=True)
def clean_expired_users():
    from userena.models import UserenaSignup
    UserenaSignup.objects.delete_expired_users()
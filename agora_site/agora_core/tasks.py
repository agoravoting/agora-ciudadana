
from agora_site.agora_core.models import Agora, Election, Profile, CastVote
from agora_site.misc.utils import *
from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora

from actstream.signals import action

from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from celery import task

import datetime

def get_base_email_context(is_secure, site_id):
    '''
    Returns a basic email context
    '''
    return dict(
            cancel_emails_url=reverse('cancel-email-updates'),
            site=Site.objects.get(pk=site_id),
            protocol=is_secure and 'https' or 'http'
        )

def cancel_start_election(election_id):
    election = Election.objects.get(pk=election_id)
    try:
        result = start_election.AsyncResult(election.task_id(start_election))
        result.revoke()
    except Exception:
        pass

def cancel_end_election(election_id):
    election = Election.objects.get(pk=election_id)
    try:
        result = end_election.AsyncResult(election.task_id(end_election))
        result.revoke()
    except Exception:
        pass

@task(ignore_result=True)
def start_election(election_id, is_secure, site_id, remote_addr):
    election = Election.objects.get(pk=election_id)

    election.voting_starts_at_date = datetime.datetime.now()
    election.create_hash()
    election.save()

    context = get_base_email_context(is_secure, site_id)

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

        if not voter.email or not voter.get_profile().email_updates:
            continue

        context['to'] = voter
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

        if not voter.email or not voter.get_profile().email_updates:
            continue

        context['to'] = voter
        datatuples.append((
            _('Vote in election %s') % election.pretty_name,
            render_to_string('agora_core/emails/election_started.txt',
                context),
            render_to_string('agora_core/emails/election_started.html',
                context),
            None,
            [voter.email]))

    send_mass_html_mail(datatuples)


@task(ignore_result=True)
def end_election(election_id, is_secure, site_id, remote_addr, user_id):
    election = Election.objects.get(pk=election_id)
    user = User.objects.get(pk=user_id)

    election.voting_extended_until_date = election.voting_ends_at_date = datetime.datetime.now()
    election.save()
    election.compute_result()

    context = get_base_email_context(is_secure, site_id)

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

        if not vote.voter.email or not vote.voter.get_profile().email_updates:
            continue

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

    send_mass_html_mail(datatuples)

    action.send(user, verb='published results', action_object=election,
        target=election.agora, ipaddr=remote_addr,
        geolocation=json.dumps(geolocate_ip(remote_addr)))


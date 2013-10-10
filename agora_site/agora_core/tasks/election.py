
from agora_site.agora_core.models import (Agora, Election, Profile, CastVote,
                                          Authority)
from agora_site.misc.utils import *
from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora

from actstream.signals import action

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.utils import translation, timezone
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from celery.contrib import rdb
from celery import task

import datetime
import requests
import uuid
import json
import os
from random import choice

@task(ignore_result=True)
def start_election(election_id, is_secure, site_id, remote_addr, user_id):
    election = Election.objects.get(pk=election_id)
    pk_fail = election.is_secure() and election.pubkey_created_at_date is None
    if not election.is_approved or election.is_archived() or pk_fail:
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
        context['allow_delegation'] = (election.agora.delegation_policy != Agora.DELEGATION_TYPE[1][0])
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
def create_pubkeys(election_id):
    election = Election.objects.get(pk=election_id)

    # if some of the pubkeys have already been created, then we will just request
    # new pubkeys for those which were not created
    #
    # also bear in mind that we know if pubkey has been created because the dir
    # in the following path exists:
    # os.path.join(settings.PRIVATE_DATA_ROOT, 'elections', 'pubkeys', session_id)
    #
    # and the status can be known if the file session_id + "_error" exist
    rdb.set_trace()
    if election.orchestra_status is not None:
        existing_session_ids = election.orchestra_status['create_election__session_ids']
        did = election.orchestra_status['create_election__director_id']
        director = Authority.objects.get(pk=did)
    else:
        election.authorities = election.agora.agora_local_authorities.all()
        election.save()
        director = choice(election.authorities.all())
        existing_session_ids = []

    now = datetime.datetime.utcnow().isoformat()
    later = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat()
    session_ids = []
    status = 'requested'
    i = 0
    for question in election.questions:
        i += 1

        # if pubkey has been created, then continue
        if len(existing_session_ids) > i and os.path.exists(
                os.path.join(settings.PRIVATE_DATA_ROOT, 'elections',
                'pubkeys', existing_session_ids[i])):
            session_ids.append(existing_session_ids[i])
            continue

        ssid = "%d_%s" % (i, str(uuid.uuid4()))
        callback_url = '%s/api/v1/update/election/%d/request_pubkey/' %\
            (settings.AGORA_BASE_URL, election.id)

        payload = {
            "session_id": ssid,
            "is_recurring": False,
            "callback_url": callback_url,
            "extra": [],
            "title": election.name,
            "url": election.url,
            "description": election.short_description,
            "question_data": question,
            # TODO: make election orchestra allow empty dates
            "voting_start_date": election.voting_starts_at_date.isoformat() if election.voting_starts_at_date else now,
            "voting_end_date": election.voting_ends_at_date.isoformat() if election.voting_ends_at_date else later,
            "authorities": [
                {
                    "name": auth.name,
                    "orchestra_url": auth.url,
                    "ssl_cert": auth.ssl_certificate
                } for auth in election.authorities.all()
            ]
        }

        r = requests.post(director.get_public_url('election'),
            data=json.dumps(payload), verify=False,
            cert=(settings.SSL_CERT_PATH,
                settings.SSL_KEY_PATH))

        if r.status_code != 202:
            status = "error requesting"

    election.orchestra_status =  {
        'create_election__session_ids': session_ids,
        'create_election__status': 'requested',
        'create_election__director_id': director.id,
        'tally_election__session_ids': [],
        'tally_election__status': '',
        'tally_election__director_id': -1,
    }
    election.save()

@task(ignore_result=True)
def clean_expired_users():
    from userena.models import UserenaSignup
    UserenaSignup.objects.delete_expired_users()

from agora_site.agora_core.models import (Agora, Election, Profile, CastVote,
                                          Authority)
from agora_site.misc.utils import *
from agora_site.agora_core.templatetags.agora_utils import get_delegate_in_agora
from agora_site.agora_core.models.voting_systems.base import (
    parse_voting_methods, get_voting_system_by_id)

from actstream.signals import action

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.utils import translation, timezone
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.crypto import constant_time_compare

from celery.contrib import rdb
from celery import task

import datetime
import codecs
import requests
import tarfile
import uuid
import json
import os
import shutil
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

    if election.extra_data and "started" in election.extra_data or\
            not election.release_tally_automatically:
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
    if election.is_secure():
        launch_encrypted_tally(election)
    else:
        election.compute_result()

    # do not send results if it's set to be done manually
    if not election.release_tally_automatically:
        return

    election.tally_released_at_date = timezone.now()
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
def release_election_results(election_id, is_secure, site_id, remote_addr, user_id):
    election = Election.objects.get(pk=election_id)

    if election.tally_released_at_date is not None:
        return

    election.tally_released_at_date = timezone.now()
    election.save()

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
    # {
    #     'election_id: "",
    #     'create_status: 'success',
    #     'create_director_id': <id>,
    #     'tally_status: 'success|requested|error requesting|error',
    #     'tally_director_id': <id>,
    # }
    election = Election.objects.get(pk=election_id)

    auths = election.authorities = election.agora.agora_local_authorities.all()
    election.save()
    if len(auths) < settings.MIN_NUM_AUTHORITIES or\
            len(auths) > settings.MAX_NUM_AUTHORITIES:
        raise Exception("Invalid number of authorities")

    director = choice(auths)
    callback_url = '%s/api/v1/update/election/%d/request_pubkey/' %\
        (settings.AGORA_BASE_URL, election.id)

    now = datetime.datetime.utcnow().isoformat()
    def isoformat(datet):
        if not datet:
            return None
        else:
            return datet.isoformat()

    payload = {
        "election_id": str(uuid.uuid4()),
        "is_recurring": False,
        "callback_url": callback_url,
        "extra": [],
        "title": election.name,
        "url": election.url,
        "description": election.short_description,
        "questions_data": election.questions,
        "voting_start_date": isoformat(election.voting_starts_at_date),
        "voting_end_date": isoformat(election.voting_ends_at_date),
        "authorities": [
            {
                "name": auth.name,
                "orchestra_url": auth.url,
                "ssl_cert": auth.ssl_certificate
            } for auth in auths
        ]
    }

    r = requests.post(director.get_public_url('election'),
        data=json.dumps(payload), verify=False,
        cert=(settings.SSL_CERT_PATH,
            settings.SSL_KEY_PATH))

    pubkey = ""
    if r.status_code != 202:
        status = "error requesting"
        pubkey = r.text
    else:
        status = 'requested'

    election.orchestra_status = {
        'election_id': payload["election_id"],
        'create_status': status,
        'create_director_id': director.id,
        'tally_status': 'not_requested_yet',
        'tally_director_id': None,
    }
    election.save()


@task(ignore_result=True)
def set_pubkeys(election_id, pubkey_data, is_secure, site_id):
    data = pubkey_data
    election = Election.objects.get(id=election_id)
    status = data['status']
    eid = data['reference']['election_id']
    now = timezone.now()

    if not isinstance(election.orchestra_status, dict) or\
            election.orchestra_status.get('create_status', '') == 'finished' or\
            election.pubkey_created_at_date is not None or\
            not constant_time_compare(election.orchestra_status.get('election_id'), eid):
        raise Exception()

    if status != 'finished':
        election.orchestra_status['create_status'] = status
        election.orchestra_status['updated_at'] = now.isoformat()
        election.save()
        raise Exception()

    # The callback comes with all the needed data, but it so happens that
    # it's not authenticated, so we get the data directly from the source
    director = get_object_or_404(Authority, pk=election.orchestra_status['create_director_id'])

    i = 0
    pubkey_list = []
    for question in election.questions:
        sid = data['session_data'][i]['session_id']
        publickey = data['session_data'][i]['pubkey']
        i += 1
        pub_url = director.get_public_data(eid, sid, "publicKey_json")
        r = requests.get(pub_url, verify=False,
            cert=(settings.SSL_CERT_PATH,
                settings.SSL_KEY_PATH))
        assert r.status_code == 200
        pubkey_downloaded = json.loads(r.text)

        if publickey != pubkey_downloaded:
            raise Exception()
        pubkey_list.append(publickey)

    election.orchestra_status['create_status'] = 'finished'
    election.orchestra_status['updated_at'] = now.isoformat()
    election.pubkeys = pubkey_list
    election.pubkey_created_at_date = now
    election.save()

    context = get_base_email_context_task(is_secure, site_id)
    context.update(dict(
        election_url=election.get_link(),
        agora_link=election.agora.get_full_name('link'),
        election_name=election.pretty_name,
        agora_name=election.agora.get_full_name()
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
            _('Election publick keys %s created') % election.pretty_name,
            render_to_string('agora_core/emails/election_pubkeys_created.txt',
                context),
            render_to_string('agora_core/emails/election_pubkeys_created.html',
                context),
            None,
            [admin.email]))

    translation.deactivate()

    send_mass_html_mail(datatuples)


def launch_encrypted_tally(election):
    '''
    Launch encrypted tally
    '''

    # stores delegation status data in the following format:
    # {
    #     'election_id: "",
    #     'create_status: 'success',
    #     'create_director_id': <id>,
    #     'tally_status: 'success|requested|error requesting|error',
    #     'tally_director_id': <id>,
    # }
    orchestra_status = JSONField(null=True)

    callback_url = '%s/api/v1/update/election/%d/do_tally/' %\
        (settings.AGORA_BASE_URL, election.id)
    auths = election.authorities.all()
    director = choice(auths)

    # create votes file and do hash. Note: currently we do not count delegated
    # votes
    votes_path = os.path.join(settings.MEDIA_ROOT, 'elections', str(election.id),
        election.orchestra_status['election_id'], 'votes')

    if os.path.exists(os.path.dirname(votes_path)):
        shutil.rmtree(os.path.dirname(votes_path))

    os.makedirs(os.path.dirname(votes_path))

    import codecs
    with codecs.open(votes_path, encoding='utf-8', mode='w') as votes_file:
        for vote in election.get_direct_votes():
            votes_file.write(json.dumps(vote.data, sort_keys=True) + "\n")


    proto = "https://" if settings.AGORA_USE_HTTPS else "http://"
    votes_url = proto + Site.objects.all()[0].domain + "/media/elections/%d/%s/votes" % (
        election.id, election.orchestra_status['election_id'])
    votes_hash = hash_file(votes_path)

    tally_data = {
        "election_id": election.orchestra_status['election_id'],
        "callback_url": callback_url,
        "extra": [],
        "votes_url": votes_url,
        "votes_hash":"sha512://" + votes_hash
    }

    r = requests.post(director.get_public_url('tally'),
        data=json.dumps(tally_data), verify=False,
        cert=(settings.SSL_CERT_PATH,
            settings.SSL_KEY_PATH))

    if r.status_code != 202:
        status = "error requesting"
    else:
        status = 'requested'

    election.orchestra_status['tally_status'] = status
    election.orchestra_status['tally_director_id'] = director.id
    election.save()


@task(ignore_result=True)
def receive_tally(election_id, tally_data, is_secure, site_id):
    data = tally_data
    election = Election.objects.get(id=election_id)
    status = data['status']
    eid = data['reference']['election_id']
    now = timezone.now()

    if not isinstance(election.orchestra_status, dict) or\
            election.orchestra_status.get('tally_status', '') == 'finished' or\
            election.voting_ends_at_date is None or\
            election.result_tallied_at_date is not None or\
            not constant_time_compare(election.orchestra_status.get('election_id'), eid):
        raise Exception()

    if status != 'finished':
        election.orchestra_status['tally_status'] = status
        election.orchestra_status['updated_at'] = now.isoformat()
        election.save()
        raise Exception()

    # The callback comes with all the needed data, but it so happens that
    # it's not authenticated, so we get the data directly from the source
    director = get_object_or_404(Authority, pk=election.orchestra_status['tally_director_id'])

    def download_file(url, where):
        r = requests.get(url, verify=False, stream=True,
            cert=(settings.SSL_CERT_PATH,
                settings.SSL_KEY_PATH))

        with open(where, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()

    pub_url = director.get_public_data(eid, "tally.tar.gz")
    tally_path = os.path.join(settings.MEDIA_ROOT, 'elections', str(election.id),
        'tally.tar.gz')

    if os.path.exists(tally_path):
        os.unlink(tally_path)

    download_file(pub_url, tally_path)
    if data['data']['tally_hash'] != "sha512://" + hash_file(tally_path):
        raise Exception()

    # untar the plaintexts
    tally_gz = tarfile.open(tally_path, mode="r:gz")
    paths = tally_gz.getnames()
    plaintexts_paths = [path for path in paths if path.endswith("/plaintexts_json")]

    i = 0
    for plaintexts_path in plaintexts_paths:
        member = tally_gz.getmember(plaintexts_path)
        extract_path =os.path.join(settings.MEDIA_ROOT, 'elections',
            str(election.id))
        member.name = "%d_plaintexts_json" % i
        tally_gz.extract(member, path=extract_path)
        i += 1

    def do_tally(tally_path, election):
        import copy
        # result is in the same format as get_result_pretty(). Initialized here
        result = copy.deepcopy(election.questions)
        base_vote =[dict(choices=[]) for q in result]

        # setup the initial data common to all voting system
        i = 0
        tallies = []
        for question in result:
            tally_type = election.election_type
            if 'tally_type' in question:
                tally_type = question['tally_type']
            voting_system = get_voting_system_by_id(tally_type)
            tally = voting_system.create_tally(election, i)
            tallies.append(tally)

            question['a'] = "question/result/" + voting_system.get_id()
            question['winners'] = []
            question['total_votes'] = 0

            for answer in question['answers']:
                answer['a'] = "answer/result/" + voting_system.get_id()
                answer['total_count'] = 0
                answer['total_count_percentage'] = 0

            tally.pre_tally(result)

            plaintexts_path = os.path.join(settings.MEDIA_ROOT, 'elections',
                str(election.id), "%d_plaintexts_json" % i)
            numChars = len(str(len(question['answers']) + 2))
            with codecs.open(plaintexts_path, encoding='utf-8', mode='r') as plaintexts_file:
                for line in plaintexts_file.readlines():
                    voter_answers = base_vote
                    try:
                        # Note line starts with " (1 character) and ends with
                        # "\n (2 characters). It contains the index of the
                        # option selected by the user but starting with 1
                        # because number 0 cannot be encrypted with elgammal
                        # so we trim beginning and end, parse the int and
                        # substract one
                        nums_str = line[1:-2]
                        nums_str = str(int(nums_str) - 1) # because crypto adds +1
                        num_zeros = len(nums_str) % numChars
                        nums_str = "0"*num_zeros + nums_str
                        voter_answers[i]['choices'] = []

                        for j in xrange(0, len(nums_str)/numChars):
                            num_str = nums_str[j*numChars:j*numChars + numChars]
                            option_index = int(num_str) - 1 # because we added +1
                            if option_index < len(question['answers']):
                                option_str = question['answers'][option_index]['value']
                            else:
                                raise Exception()

                            # craft the voter_answers in the format admitted by
                            # tally.add_vote
                            voter_answers[i]['choices'].append(option_str)
                    except:
                        print "invalid vote: " + line
                        print "voter_answers = " + json.dumps(voter_answers)
                        import traceback; print traceback.format_exc()

                    tally.add_vote(voter_answers=voter_answers,
                        result=result, is_delegated=False)

            i += 1


        if not election.extra_data:
            election.extra_data = dict()

        # post process the tally
        for tally in tallies:
            tally.post_tally(result)

        election.electorate = election.agora.members.all()
        election.result = dict(
            a= "result",
            counts = result,
            total_votes = result[0]['total_votes'] + result[0]['dirty_votes'],
            electorate_count = election.electorate.count(),
            total_delegated_votes = 0
        )

        tally_log = []
        for tally in tallies:
            tally_log.append(tally.get_log())
        election.extra_data['tally_log'] = tally_log

        election.delegated_votes_frozen_at_date = election.voters_frozen_at_date =\
            election.result_tallied_at_date = timezone.now()

    do_tally(tally_path, election)
    election.orchestra_status['tally_status'] = 'finished'
    election.orchestra_status['updated_at'] = now.isoformat()
    election.result_tallied_at_date = now
    election.save()

@task(ignore_result=True)
def clean_expired_users():
    from userena.models import UserenaSignup
    UserenaSignup.objects.delete_expired_users()

# -*- coding: utf-8 -*-

from south.db import db
from south.v2 import SchemaMigration

from django.db import models
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.importlib import import_module
from django import forms as django_forms
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

import random
import datetime

class Plurality(object):
    '''
    Defines the helper functions that allows agora to manage a voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'ONE_CHOICE'

    @staticmethod
    def get_description():
        return _('Simple one choice result type of election')

    @staticmethod
    def create_tally(election):
        '''
        Create object that helps to compute the tally
        '''
        return PluralityTally(election)

    @staticmethod
    def get_question_field(election, question):
        '''
        Creates a voting field that can be used to answer a question in a ballot
        '''
        answers = [(answer['value'], answer['value'])
            for answer in question['answers']]
        random.shuffle(answers)

        return django_forms.ChoiceField(label=question, choices=answers,
            required=True)


class PluralityTally(object):
    '''
    Class oser to tally an election
    '''
    election = None

    def __init__(self, election):
        self.election

    def pre_tally(self, result):
        '''
        Pre-proccess the tally
        '''
        for question in result:
            for answer in question['answers']:
                answer['by_direct_vote_count'] = 0
                answer['by_delegation_count'] = 0

    def add_vote(self, voter_answers, result, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        i = 0
        for question in result:
            for answer in question['answers']:
                if answer['value'] in voter_answers[i]["choices"]:
                    answer['total_count'] += 1
                    if is_delegated:
                        answer['by_delegation_count'] += 1
                    else:
                        answer['by_direct_vote_count'] += 1
                    break
            i += 1

    def post_tally(self, result):
        '''
        Post process the tally
        '''
        # all votes counted, finish result will contain the actual result in
        # JSON format, something like:
        #[
            #{
                #"a": "question/result/ONE_CHOICE",
                #"answers": [
                    #{
                        #"a": "answer/result/ONE_CHOICE",
                        #"value": "Alice",
                        #"total_count": 33,
                        #"total_count_percentage": 73.4,
                        #"by_direct_vote_count": 25,
                        #"by_delegation_count": 8,
                        #"url": "<http://alice.com>", # UNUSED ATM
                        #"details": "Alice is a wonderful person who..." # UNUSED ATM
                    #},
                    #...
                #],
                #"max": 1, "min": 0,
                #"question": "Who Should be President?",
                #"randomize_answer_order": false, # true by default
                #"short_name": "President", # UNSED ATM
                #"tally_type": "ONE_CHOICE"
                #"winners": ["Alice"]
            #},
            #...
        #]

        i = 0
        # post process the tally adding additional information like total_count
        # in each answer, etc
        for question in result:
            total_votes = 0
            winner = None

            for answer in question['answers']:
                total_votes += answer['total_count']
                if not winner or answer['total_count'] > winner['total_count']:
                    winner = answer

            question['total_votes'] = total_votes
            question['winners'] = [winner['value']]

            for answer in question['answers']:
                if total_votes > 0:
                    answer['total_count_percentage'] = (answer['total_count'] * 100.0) / total_votes
                else:
                    answer['total_count_percentage'] = 0

def compute_result(election, orm):
    '''
    Computes the result of the election
    '''

    # maximum delegation depth, so that we don't enter in near-infinite loops
    MAX_DELEGATION_DEPTH = 20

    # Query with the direct votes in this election
    q=election.cast_votes.filter(
        is_counted=True,
        invalidated_at_date=None
    ).values('voter__id').query

    # Query with the delegated votes
    election.delegated_votes = orm.CastVote.objects.filter(
        election=election.agora.delegation_election,
        is_direct=False,
        is_counted=True,
        invalidated_at_date=None
        # we exclude from this query the people who voted directly so that
        # you cannot vote twice
    ).exclude(
        is_direct=False,
        voter__id__in=q
    )

    # These are all the people that can vote in this election
    election.electorate = election.agora.members.all()

    # These are all the direct votes, even from those who are not elegible 
    # to vote in this election
    nodes = election.cast_votes.filter(is_direct=True,
        #is_counted=True, FIXME
        invalidated_at_date=None)

    # These are all the delegation votes, i.e. those that point to a delegate
    #edges = election.agora.delegation_election.cast_votes.filter(
        #is_direct=False, invalidated_at_date=None)
    edges = election.delegated_votes

    # list of saved paths. A path represent a list of users who delegate
    # into a given vote.
    # A path has the following format:
    #{
        #user_ids: [id1, id2, ...],
        #answers: [ question1_plaintext_answer, question2_plaintext_answer, ..],
        #is_broken_loop: True|False
    #}
    # note that the user_ids do NOT include the last user in the chain
    # also note that is_broken_loop is set to true if either the loop is
    # closed (infinite) or does not end in a leaf (=node)
    paths = []

    # A dictionary where the number of delegated voted per delegate is
    # stored. This dict is used only for recording the number of delegated
    # votes a delegate has.
    #
    # The keys are the user_ids of the delegates, and the values are
    # the number of delegated votes.
    # Note that because of chains of delegations, the same vote can be
    # counted multiple times.
    delegation_counts = dict() 

    def get_delegate(vote):
        if vote.data['a'] != 'delegated-vote' or not is_plaintext(vote):
            raise Exception('This kind of vote does not have delegate user')
        else:
            return get_object_or_404(User, username=get_delegate_id(vote))


    def is_plaintext(vote):
        if vote.data['a'] == 'vote':
            return vote.data['answers'][0]['a'] == 'plaintext-answer'
        elif vote.data['a'] == 'delegated-vote':
            return True
        else:
            return True

    def get_delegate_id(vote):
        if vote.data['a'] != 'delegated-vote' or not is_plaintext(vote):
            raise Exception('This kind of vote does not have delegate user')
        else:
            return vote.data['answers'][0]['choices'][0]['username']

    def update_delegation_counts(vote):
        '''
        function used to update the delegation counts, for each valid vote.
        it basically goes deep in the delegation chain, updating the count
        for each delegate
        '''
        # if there is no vote we have nothing to do
        if not vote:
            return

        def increment_delegate(delegate_id):
            '''
            Increments the delegate count or sets it to one if doesn't it
            exist
            '''
            if delegate_id in delegation_counts:
                delegation_counts[delegate_id] += 1
            else:
                delegation_counts[delegate_id] = 1

        i = 0
        while not vote.is_direct and i < MAX_DELEGATION_DEPTH:
            i += 1
            next_delegate = get_delegate(vote)
            if nodes.filter(voter=next_delegate).count() == 1:
                increment_delegate(next_delegate.id)
                return
            elif edges.filter(voter=next_delegate).count() == 1:
                increment_delegate(next_delegate.id)
                vote = edges.filter(voter=next_delegate)[0]
            else:
                raise Exception('Broken delegation chain')

    def get_path_for_user(user_id):
        '''
        Given an user id, checks if it's already in any known path, and 
        return it if that path is found. Returns None otherwise.
        '''
        for path in paths:
            if user_id in path["user_ids"]:
                return path
        return None

    def get_vote_for_voter(voter):
        '''
        Given a voter (an User), returns the vote of the vote of this voter
        on the election. It will be either a proxy or a direct vote
        '''
        if nodes.filter(voter=voter).count() == 1:
            return nodes.filter(voter=voter)[0]
        elif edges.filter(voter=voter) == 1:
            return edges.filter(voter=voter)[0]
        else:
            return None

    voting_system = Plurality
    tally = voting_system.create_tally(election)

    import copy
    # result is in the same format as get_result_pretty(). Initialized here
    result = copy.deepcopy(election.questions)

    # setup the initial data common to all voting system
    for question in result:
        question['a'] = "question/result/" + voting_system.get_id()
        question['winners'] = []
        question['tally_type'] = voting_system.get_id()
        question['total_votes'] = 0

        for answer in question['answers']:
            answer['a'] = "answer/result/" + voting_system.get_id()
            answer['total_count'] = 0
            answer['total_count_percentage'] = 0

    # prepare the tally
    tally.pre_tally(result)

    def add_vote(user_answers, is_delegated):
        '''
        Given the answers of a vote, update the result
        '''
        tally.add_vote(voter_answers=user_answers, result=result,
            is_delegated=is_delegated)

    # Here we go! for each voter, we try to find it in the paths, or in
    # the proxy vote chain, or in the direct votes pool
    for voter in election.electorate.all():
        path_for_user = get_path_for_user(voter.id)

        # Found the user in a known path
        if path_for_user and not path_for_user['is_broken_loop']:
            # found a path to which the user belongs

            # update delegation counts
            update_delegation_counts(get_vote_for_voter(voter))
            add_vote(path_for_user['answers'], is_delegated=True)
        # found the user in a direct vote
        elif nodes.filter(voter=voter).count() == 1:
            vote = nodes.filter(voter=voter)[0]
            add_vote(vote.data["answers"], is_delegated=False)
        # found the user in an edge (delegated vote), but not yet in a path
        elif edges.filter(voter=voter).count() == 1:
            path = dict(
                user_ids=[voter.id],
                answers=[],
                is_broken_loop=False
            )

            current_edge = edges.filter(voter=voter)[0]
            loop = True
            i = 0
            while loop and i < MAX_DELEGATION_DEPTH:
                i += 1
                delegate = get_delegate(current_edge)
                path_for_user = get_path_for_user(delegate.id)
                check_depth = i < MAX_DELEGATION_DEPTH

                if check_depth and delegate in path['user_ids']:
                    # wrong path! loop found, vote won't be counted
                    path['is_broken_loop'] = True
                    paths += [path]
                    loop = False
                elif check_depth and path_for_user and not path_for_user['is_broken_loop']:
                    # extend the found path and count a new vote
                    path_for_user['user_ids'] += path['user_ids']

                    # Count the vote
                    add_vote(path_for_user['answers'], is_delegated=True)
                    update_delegation_counts(current_edge)
                    loop = False
                elif check_depth and nodes.filter(voter=delegate).count() == 1:
                    # The delegate voted directly, add the path and count
                    # the vote
                    vote = nodes.filter(voter=delegate)[0]
                    path["answers"]=vote.data['answers']
                    paths += [path]
                    add_vote(vote.data['answers'], is_delegated=True)
                    update_delegation_counts(current_edge)
                    loop = False

                elif check_depth and edges.filter(voter=delegate).count() == 1:
                    # the delegate also delegated, so continue looping
                    path['user_ids'] += [delegate.id]
                    current_edge = edges.filter(voter=delegate)[0]
                else:
                    # broken path! we cannot continue
                    path['is_broken_loop'] = True
                    paths += [path]
                    loop = False

    # post process the tally
    tally.post_tally(result)

    election.result = dict(
        a= "result",
        counts = result,
        delegation_counts = delegation_counts,
    )

    # TODO: update result_hash
    election.save()


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Election.delegated_votes_result'
        db.delete_column('agora_core_election', 'delegated_votes_result')

        # reprocess the past elections
        if not db.dry_run:
            elections = orm.Election.objects.filter(
                result_tallied_at_date__isnull=False, 
                archived_at_date__isnull=True)
            for election in elections:
                date = election.result_tallied_at_date
                compute_result(election, orm)
                election.result_tallied_at_date = date


    def backwards(self, orm):
        # Adding field 'Election.delegated_votes_result'
        db.add_column('agora_core_election', 'delegated_votes_result',
                      self.gf('agora_site.misc.utils.JSONField')(null=True),
                      keep_default=False)


    models = {
        'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'geolocation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipaddr': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'timezone.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'agora_core.agora': {
            'Meta': {'unique_together': "(('name', 'creator'),)", 'object_name': 'Agora'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'administrated_agoras'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'archived_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'biography': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'comments_policy': ('django.db.models.fields.CharField', [], {'default': "'ANYONE_CAN_COMMENT'", 'max_length': '50'}),
            'created_at_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_agoras'", 'to': "orm['auth.User']"}),
            'delegation_election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'delegation_agora'", 'null': 'True', 'to': "orm['agora_core.Election']"}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'ONE_CHOICE'", 'max_length': '50'}),
            'eligibility': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'extra_data': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'is_vote_secret': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'agoras'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'membership_policy': ('django.db.models.fields.CharField', [], {'default': "'ANYONE_CAN_JOIN'", 'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'pretty_name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'})
        },
        'agora_core.castvote': {
            'Meta': {'unique_together': "(('election', 'voter', 'casted_at_date'),)", 'object_name': 'CastVote'},
            'action_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'null': 'True'}),
            'casted_at_date': ('django.db.models.fields.DateTimeField', [], {}),
            'data': ('agora_site.misc.utils.JSONField', [], {}),
            'election': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cast_votes'", 'to': "orm['agora_core.Election']"}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidated_at_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'is_counted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_direct': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tiny_hash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cast_votes'", 'to': "orm['auth.User']"})
        },
        'agora_core.election': {
            'Meta': {'object_name': 'Election'},
            'agora': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'elections'", 'null': 'True', 'to': "orm['agora_core.Agora']"}),
            'approved_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'archived_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'comments_policy': ('django.db.models.fields.CharField', [], {'default': "'ANYONE_CAN_COMMENT'", 'max_length': '50'}),
            'created_at_date': ('django.db.models.fields.DateTimeField', [], {}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_elections'", 'to': "orm['auth.User']"}),
            'delegated_votes': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'delegated_votes'", 'symmetrical': 'False', 'to': "orm['agora_core.CastVote']"}),
            'delegated_votes_frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'election_type': ('django.db.models.fields.CharField', [], {'default': "'ONE_CHOICE'", 'max_length': '50'}),
            'electorate': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'elections'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'eligibility': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'extra_data': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_vote_secret': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified_at_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'parent_election': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'children_elections'", 'null': 'True', 'to': "orm['agora_core.Election']"}),
            'pretty_name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'questions': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'result': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'result_tallied_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'tiny_hash': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'null': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'voters_frozen_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_ends_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'voting_extended_until_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'voting_starts_at_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'})
        },
        'agora_core.profile': {
            'Meta': {'object_name': 'Profile'},
            'biography': ('django.db.models.fields.TextField', [], {}),
            'email_updates': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'extra': ('agora_site.misc.utils.JSONField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lang_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '5'}),
            'last_activity_read_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'timezone.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'timezone.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['agora_core']
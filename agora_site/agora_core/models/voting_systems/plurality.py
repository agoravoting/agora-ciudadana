import random

from django import forms as django_forms
from django.utils.translation import ugettext_lazy as _

from .base import BaseVotingSystem, BaseTally
from agora_site.misc.utils import *
from agora_site.agora_core.models.voting_systems.base import (
    parse_voting_methods, get_voting_system_by_id, base_question_check)

class Plurality(BaseVotingSystem):
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
        return _('Choose one option among many - Technical name: Plurality voting system')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return PluralityTally(election, question_num)

    @staticmethod
    def get_question_field(election, question):
        '''
        Creates a voting field that can be used to answer a question in a ballot
        '''
        answers = [(answer['value'], answer['value'])
            for answer in question['answers']]
        random.shuffle(answers)

        return PluralityField(label=question['question'],
            choices=answers, required=True, election=election, question=question)

    @staticmethod
    def validate_question(question):
        '''
        Validates the value of a given question in an election
        '''
        error = django_forms.ValidationError(_('Invalid questions format'))
        base_question_check(question)

        if question['min'] > 1 or question['max'] != 1:
            raise error


class PluralityField(django_forms.ChoiceField):
    '''
    A field that returns a valid answer text
    '''
    election = None

    def __init__(self, *args, **kwargs):
        self.election = kwargs['election']
        del kwargs['election']

        self.question = kwargs['question']
        del kwargs['question']

        return super(PluralityField, self).__init__(*args, **kwargs)

    def clean(self, value):
        """
        Wraps the choice field the proper way
        """
        error = django_forms.ValidationError(_('Invalid questions format'))
        if self.election.is_secure():
            if not isinstance(value, dict):
                raise error

            elements = ["alpha", "beta", "commitment", "challenge", "response"]
            parsed_els = dict()
            for el in elements:
                assert el in value and isinstance(value[el], basestring)
                parsed_els[el] = int(value[el])

            assert len(elements) == len(parsed_els.keys())

            # find question in election
            question = None
            q_i = 0
            for q in self.election.questions:
                if q['question'] == self.label:
                    question = q
                    break
                q_i += 1

            pubkey = self.election.pubkeys[q_i]
            pubkey_parsed = dict(
                p=int(pubkey["p"]),
                g=int(pubkey["g"])
            )
            verify_pok_plaintext(pubkey_parsed, parsed_els)
            return value
        else:
            if value or self.question['min'] > 0:
                clean_value = super(PluralityField, self).clean(value)
                return {
                    "a": "plaintext-answer",
                    "choices": [clean_value],
                }
            else:
                return {
                    "a": "plaintext-answer",
                    "choices": [],
                }


class PluralityTally(BaseTally):
    '''
    Class to tally an election
    '''
    dirty_votes = 0

    def pre_tally(self, result):
        '''
        Pre-proccess the tally
        '''
        question = result[self.question_num]
        for answer in question['answers']:
            answer['by_direct_vote_count'] = 0
            answer['by_delegation_count'] = 0

    def add_vote(self, voter_answers, result, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        question = result[self.question_num]
        for answer in question['answers']:
            if answer['value'] in voter_answers[self.question_num]["choices"]:
                answer['total_count'] += 1
                if is_delegated:
                    answer['by_delegation_count'] += 1
                else:
                    answer['by_direct_vote_count'] += 1
                break
        if not voter_answers[self.question_num]["choices"]:
            self.dirty_votes += 1

    def parse_vote(self, number, question):
        if number < len(question['answers']):
            option_str = question['answers'][number]['value']
        if number >= len(question['answers']):
            option_str = ""

        return [option_str]

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
            #},
            #...
        #]

        # post process the tally adding additional information like total_count
        # in each answer, etc
        question = result[self.question_num]
        total_votes = 0
        winner = None

        for answer in question['answers']:
            total_votes += answer['total_count']
            if not winner or answer['total_count'] > winner['total_count']:
                winner = answer

        question['total_votes'] = total_votes
        question['dirty_votes'] = self.dirty_votes
        question['winners'] = [winner['value']]

        for answer in question['answers']:
            if total_votes > 0:
                answer['total_count_percentage'] = (answer['total_count'] * 100.0) / total_votes
            else:
                answer['total_count_percentage'] = 0
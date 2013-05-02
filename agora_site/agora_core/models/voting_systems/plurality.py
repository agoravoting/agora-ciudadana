import random

from django import forms as django_forms
from django.utils.translation import ugettext_lazy as _

from .base import BaseVotingSystem, BaseTally
from agora_site.misc.utils import *

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

        if question['a'] != 'ballot/question' or\
            not isinstance(question['min'], int) or question['min'] < 0 or\
            question['min'] > 1 or\
            not isinstance(question['max'], int) or question['max'] != 1 or\
            not isinstance(question['randomize_answer_order'], bool):
            raise error

        # check there are at least 2 possible answers
        if not isinstance(question['answers'], list) or\
            len(question['answers']) < 2:
            raise error

        # check each answer
        for answer in question['answers']:
            if not isinstance(answer, dict):
                raise error

            # check it contains the valid elements
            if not list_contains_all(['a', 'value', 'url', 'details'],
                answer.keys()):
                raise error

            for el in ['a', 'value', 'url', 'details']:
                if not (isinstance(answer[el], unicode) or\
                    isinstance(answer[el], str)) or\
                    len(answer[el]) > 500:
                    raise error

            if answer['a'] != 'ballot/answer' or\
                not (
                    isinstance(answer['value'], unicode) or\
                    isinstance(answer['value'], str)
                ) or len(answer['value']) < 1:
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
        if value or self.question['min'] > 0:
            clean_value = super(PluralityField, self).clean(value)
        else:
            clean_value = ""

        # NOTE: in the future, when encryption support is added, this will be
        # handled differently, probably in a more generic way so that
        # PluralityField doesn't know anything about plaintext or encryption.
        return {
            "a": "plaintext-answer",
            "choices": [clean_value],
        }

class PluralityTally(BaseTally):
    '''
    Class to tally an election
    '''

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
        question['winners'] = [winner['value']]

        for answer in question['answers']:
            if total_votes > 0:
                answer['total_count_percentage'] = (answer['total_count'] * 100.0) / total_votes
            else:
                answer['total_count_percentage'] = 0
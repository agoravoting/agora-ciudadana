import random

from django import forms as django_forms
from django.utils.translation import ugettext_lazy as _

from .base import BaseVotingSystem, BaseTally

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


class PluralityTally(BaseTally):
    '''
    Class oser to tally an election
    '''

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
            question['winner'] = winner['value']

            for answer in question['answers']:
                if total_votes > 0:
                    answer['total_count_percentage'] = (answer['total_count'] * 100.0) / total_votes
                else:
                    answer['total_count_percentage'] = 0
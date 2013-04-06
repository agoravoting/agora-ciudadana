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
    def add_vote(self, voter_answers, result, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        i = 0
        for question in result:
            for answer in question['answers']:
                if answer['value'] in voter_answers[i]["choices"]:
                    if is_delegated:
                        answer['by_delegation_count'] += 1
                    else:
                        answer['by_direct_vote_count'] += 1
                    break
            i += 1
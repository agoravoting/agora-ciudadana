from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.importlib import import_module
from django import forms as django_forms
from agora_site.misc.utils import *

def get_voting_system_classes():
    '''
    Returns a list with the available voting system classes
    '''
    voting_methods = settings.VOTING_METHODS
    ret_list = []
    for voting_method in voting_methods:
        mod_path, klass_name = voting_method.rsplit('.', 1)
        mod = import_module(mod_path)
        klass = getattr(mod, klass_name, None)
        ret_list.append(klass)
    return ret_list

def parse_voting_methods():
    '''
    Returns a tuple of pairs with the id and description of the voting system
    classes
    '''
    classes = get_voting_system_classes()
    return tuple(
        [(k.get_id(), k.get_description()) for k in classes]
    )

def get_voting_system_by_id(name):
    '''
    Returns the voting system klass given the id, or None if not found
    '''
    classes = get_voting_system_classes()
    for klass in classes:
        if klass.get_id() == name:
            return klass
    return None

def base_question_check(question):
    '''
    Validates the value of a given question in an election
    '''
    error = django_forms.ValidationError(_('Invalid questions format'))

    if question['question'].strip() != clean_html(question['question'], True):
        raise error

    if question['a'] != 'ballot/question' or\
        not isinstance(question['min'], int) or question['min'] < 0 or\
        not isinstance(question['max'], int) or\
        question['max'] < question['min'] or\
        not isinstance(question['randomize_answer_order'], bool):
        raise error

    # check there are at least 2 possible answers
    if not isinstance(question['answers'], list) or\
        len(question['answers']) < 2:
        raise error

    if not isinstance(question['layout'], basestring) or\
        question['layout'] not in ['SIMPLE', 'PRIMARY']:
        raise error

    # check each answer
    answer_values = []
    for answer in question['answers']:
        if not isinstance(answer, dict):
            raise error

        if answer['value'] in answer_values:
            raise error
        answer_values.append(answer['value'])

        # check it contains the valid elements
        if not list_contains_all(['a', 'value'], answer.keys()):
            raise error

        for key in answer.keys():
            if key not in ['a', 'value', 'media_url', 'urls', 'details',
                           'details_title']:
                raise error

        for el in ['a', 'value']:
            if not isinstance(answer[el], basestring) or\
                len(answer[el]) > 500:
                raise error

        if answer['a'] != 'ballot/answer' or\
                not isinstance(answer['value'], basestring) or\
                len(answer['value']) < 1:
            raise error

        if answer['value'].strip() != clean_html(answer['value'], True).replace("\n", ""):
            raise error

        if question['layout'] == 'PRIMARY':
            if not list_contains_all(['media_url', 'urls', 'details',
                    'details_title'], answer.keys()):
                raise error

            if not isinstance(answer['media_url'], basestring) or\
                    len(answer['details_title']) > 500:
                raise error

            if not isinstance(answer['details_title'], basestring) or\
                    len(answer['details_title']) > 500:
                raise error

            if not isinstance(answer['details'], basestring) or\
                    len(answer['details']) > 5000:
                raise error

            if answer['details'].strip().replace("\n", "") != clean_html(answer['details'], False).replace("\n", "").strip():
                raise error

            if not isinstance(answer['urls'], list) or\
                    len(answer['urls']) > 10:
                raise error

            for url in answer['urls']:
                if not isinstance(url, dict):
                    raise error
                for key, value in url.items():
                    if key not in ['title', 'url']:
                        raise error
                    if not isinstance(value, basestring) or len(value) > 500:
                        raise error


class BaseVotingSystem(object):
    '''
    Defines the helper functions that allows agora to manage a voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'base'

    @staticmethod
    def get_description():
        '''
        Returns the user text description of the voting system
        '''
        pass

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return BaseTally(election, question_num)

    @staticmethod
    def get_question_field(election, question):
        '''
        Creates a voting field that can be used to answer a question in a ballot
        '''
        pass

    @staticmethod
    def validate_question(question):
        '''
        Validates the value of a given question in an election. Raises a
        django_forms.ValidationError exception if validation fails
        '''
        pass

class BaseTally(object):
    '''
    Class oser to tally an election
    '''
    election = None
    question_num = None

    def __init__(self, election, question_num):
        self.election = election
        self.question_num = question_num
        self.init()

    def init(self):
        pass

    def pre_tally(self, result):
        '''
        Function called once before the tally begins
        '''
        pass

    def add_vote(self, voter_answers, result, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        pass

    def post_tally(self, result):
        '''
        Once all votes have been added, this function is called once
        '''
        pass

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return None
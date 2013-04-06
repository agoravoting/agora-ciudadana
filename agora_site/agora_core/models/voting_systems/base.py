from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.importlib import import_module

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
    def create_tally(election):
        '''
        Create object that helps to compute the tally
        '''
        return BaseTally(election)

    @staticmethod
    def get_question_field(election, question):
        '''
        Creates a voting field that can be used to answer a question in a ballot
        '''
        pass

class BaseTally(object):
    '''
    Class oser to tally an election
    '''
    election = None

    def __init__(self, election):
        self.election

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

from __future__ import unicode_literals
import random
import copy
import sys

from django import forms as django_forms
from django.utils.translation import ugettext_lazy as _

from .base import BaseVotingSystem, BaseTally
from agora_site.misc.utils import *

class WrightSTV(BaseVotingSystem):
    '''
    Defines the helper functions that allows agora to manage a voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'WRIGHT-STV'

    @staticmethod
    def get_description():
        return _('Rank some options among many - Technical name: Wright STV (Single Transferable Vote)')

    @staticmethod
    def create_tally(election):
        '''
        Create object that helps to compute the tally
        '''
        return WrightSTVTally(election)

    @staticmethod
    def get_question_field(election, question):
        '''
        Creates a voting field that can be used to answer a question in a ballot
        '''
        answers = [(answer['value'], answer['value'])
            for answer in question['answers']]
        random.shuffle(answers)

        return WrightSTVField(label=question['question'],
            choices=answers, required=True, election=election)

    @staticmethod
    def validate_question(question):
        '''
        Validates the value of a given question in an election
        '''
        error = django_forms.ValidationError(_('Invalid questions format'))

        if 'num_seats' not in question or\
            not isinstance(question['num_seats'], int) or\
            question['num_seats'] < 1:
            return error

        if question['a'] != 'ballot/question' or\
            not isinstance(question['min'], int) or question['min'] < 0 or\
            question['min'] > 1 or\
            not isinstance(question['max'], int) or question['max'] < 1 or\
            not isinstance(question['randomize_answer_order'], bool):
            raise error

        # check there are at least 2 possible answers
        if not isinstance(question['answers'], list) or\
            len(question['answers']) < 2 or\
            len(question['answers']) < question['num_seats'] or\
            len(question['answers']) > 100:
            raise error

        # check each answer
        answer_values = []
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

            if answer['value'] in answer_values:
                raise error
            answer_values.append(answer['value'])


class WrightSTVField(JSONFormField):
    '''
    A field that returns a valid answer text
    '''
    election = None

    def __init__(self, choices, election, *args, **kwargs):
        self.election = election
        return super(WrightSTVField, self).__init__(*args, **kwargs)

    def clean(self, value):
        """
        Wraps the choice field the proper way
        """
        error = django_forms.ValidationError(_('Invalid answer format'))
        clean_value = super(WrightSTVField, self).clean(value)

        if not isinstance(value, list):
            raise error

        # check for repeated answers
        if len(value) != len(set(value)):
            raise error

        # find question in election
        question = None
        for q in self.election.questions:
            if q['question'] == self.label:
                question = q

        # gather possible answers
        possible_answers = [answer['value'] for answer in question['answers']]

        # check the answers provided are valid
        for i in value:
            if i not in possible_answers:
                raise error

        # NOTE: in the future, when encryption support is added, this will be
        # handled differently, probably in a more generic way so that
        # WrightSTVField doesn't know anything about plaintext or encryption.
        return {
            "a": "plaintext-answer",
            "choices": clean_value,
        }


class WrightSTVTally(BaseTally):
    '''
    Class to tally a wright stv election
    '''
    # list containing the current list of ballots.
    # In each iteration this list is modified. For efficiency, ballots with the
    # same ordered choices are grouped. The format of each item in this list is
    # the following:
    #
    #{
        #'votes': 12, # number of ballots with this selection of choices
        #'answers': [2, 1, 4] # list of ids of the choices
    #}
    ballots = []

    # int var that stores the number of winners/seats
    num_seats = 1

    total_number_of_ballots = 0

    # dict that has as keys the possible answer['value'], and as value the id
    # of each answer. 
    # Used because internally we store the answers by id with a number to speed
    # things up.
    answer_to_ids_dict = dict()

    # reverse dict. Keys are coerced to strings
    ids_to_answer_dict = dict()

    appointed_seats = 0
    appointed_seats_list = []

    # list of the iterations. 
    # Contains a detailed and structured log of the actions taken and the
    # data generated in each step. For each step, the format is the following:
    #
    #{
        #'answers': { # each key is a not-eliminated answer
            #'answer1' : {
                #'votes': 73.51, 
                #'received': 12.5,
                #'transferred': 0,

                ## status stablishes the state of the option. possible values
                ## are:
                ## * contesting: the option is not being eliminated in this
                ##   round, but it didn't reach quota either
                ##
                ## * elected: the option passed the quota and is elected
                ##   in this round. if it's the last round, it means this is a
                ##   winner. If it's not the last round, it only means that the
                ##   option was provisionally elected.
                ##
                ## * eliminated: this is the option that gathered less points in
                ##   this round and thus was eliminated for the next round.
                #'status': 'contesting',
            #},
        #},
        #'exhausted': {
            #'votes': 10,
        #}
        #'quota': 76 # quota for this round
    #}
    iterations = []

    def pre_tally(self, result):
        '''
        Pre-proccess the tally
        '''
        self.num_seats = result[0]['num_seats']

        i = 0
        # we assume only one question
        for answer in result[0]['answers']:
            self.answer_to_ids_dict[answer['value']] = i
            self.ids_to_answer_dict[str(i)] = answer['value']
            i += 1

    def answer2id(self, answer):
        '''
        Converts the answer to an id. 
        @return the id or -1 if not found
        '''
        return self.answer_to_ids_dict.get(answer, -1)

    def id2answer(self, id_num):
        '''
        Converts the id to an answer. 
        '''
        return self.ids_to_answer_dict.get(str(id_num), '')

    def find_ballot(self, answers):
        '''
        Find a ballot with the same answers as the one given in self.ballots. 
        Returns the ballot or None if not found.
        '''
        for ballot in self.ballots:
            if ballot['answers'] == answers:
                return ballot

        return None

    def add_vote(self, voter_answers, result, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        # we assume only one question
        answers = [self.answer2id(a) for a in voter_answers[0]['choices']]

        # we got ourselves an invalid vote, don't count it
        if -1 in answers:
            return

        ballot = self.find_ballot(answers)
        self.total_number_of_ballots += 1
        # if ballot found, increment the count. Else, create a ballot and add it
        if ballot:
            ballot['votes'] += 1
        else:
            self.ballots.append(dict(votes=1, answers=answers))

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return self.iterations

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
                        #"elected": False,
                        #"seat_number": 0, # 0 means non elected
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

        self.appointed_seats = 0
        self.appointed_seats_list = []
        total_votes = 0
        quota = 0
        minor_answer_count = -1

        # used to force a new iteration when too many seats were selected
        force_iteration = False

        def recalculate_quota(iteration):
            '''
            Recalculates the quota using Droop's quota
            '''
            iteration['quota'] =  quota = int(total_votes / (self.num_seats + 1.0)) + 1

        def effective_count(answer):
            '''
            Calculates count + received + transferred

            Note that when an answer has been provisionally elected, the
            transfer_surplus function modifies the count subtracting to it
            the <transferred> amount. That's why we add <transferred> instead
            of substract it in here.
            '''
            return answer['votes'] + answer['received'] + answer['transferred']

        def recalculate_appointed_seats(iteration):
            '''
            Taking into account the current quota, recalculates the
            number of appointed seats
            '''
            self.appointed_seats = 0
            self.appointed_seats_list = []
            minor_answer_count = sys.maxint
            for key, value in iteration['answers'].iteritems():
                count = effective_count(value)
                if count >= iteration['quota']:
                    self.appointed_seats += 1
                    self.appointed_seats_list.append((key, self.answer2id(key)))
                    value['status'] = 'elected'
                if count < minor_answer_count:
                    minor_answer_count = count

            # order appointed_seats_list in reverse effective count order
            self.appointed_seats_list = sorted(self.appointed_seats_list, reverse=True,
                key=lambda seat: effective_count(iteration['answers'][seat[0]]))

        def count_first_choice_votes(all_answers):
            '''
            Given a dict with keys being the answer titles and values a dict
            with the key "votes" available, takes self.ballots to fill votes
            with the number of ballots containing the answer as the first
            choice
            '''
            # reset the count of total votes
            global total_votes
            total_votes = 0
            for ballot in self.ballots:
                first_answer_id = ballot['answers'][0]
                first_answer = self.id2answer(first_answer_id)

                all_answers[first_answer]['votes'] += ballot['votes']
                total_votes += ballot['votes']

        def transfer_surplus(iteration):
            '''
            Transfer elected answers surplus to any answer where the elected
            answers were the first option and the answer was the second.
            '''
            appointed_seats_dict = dict(self.appointed_seats_list)

            processed_seat_ids = []

            def next_seat_to_process(processed_seat_ids):
                '''
                Taking into account the list of processed_seat_ids, returns the
                next seat to process from appointed_seats_list. 
                If there are no remaining seats to process, then returns
                (None, -1)
                '''
                for (seat, seat_id) in self.appointed_seats_list:
                    if seat_id not in processed_seat_ids:
                        return (seat, seat_id)
                return (None, -1)

            def index_next_choice(answers):
                for i in xrange(len(ballot['answers']) - 1):
                    if ballot['answers'][i + 1] not in appointed_seats_dict.values():
                        return i + 1
                return -1

            def add_second_choice(ballot, index, second_choices):
                answer_id = ballot['answers'][index]
                answer = self.id2answer(answer_id)

                if answer in second_choices:
                    second_choices[answer] += ballot['votes']
                else:
                    second_choices[answer] = ballot['votes']


            # For each appointed seat, we apply the transfer surplus algorithm
            # NOTE that after processing an appointed seat the appointed
            # seats list is recalculated, so we cannot directly iterate a
            # changing list.
            while True:
                seat, seat_id = next_seat_to_process(processed_seat_ids)

                # no more seats to process
                if seat_id < 0:
                    break

                # handy seat_answer from the iteration
                seat_answer = iteration['answers'][seat]

                # total amount of votes to transfer
                transferred = seat_answer['transferred'] = effective_count(seat_answer) - iteration['quota']

                # transfer surplus in the seat_answer
                seat_answer['votes'] = iteration['quota']

                # num_ballots in which to transfer the surplus
                num_ballots = 0

                # for each non elected candidate, the key is the candidate name
                # and the value the number of ballots where the first choice
                # was seat_answer and the send the mentioned candidate.
                second_choices = dict()

                # num of votes exhausted in this appointment
                exhausted = 0

                # calculate second_choices
                for ballot in self.ballots:
                    if ballot['answers'][0] != seat_id:
                        continue

                    index = index_next_choice(ballot)
                    if index < 0:
                        exhausted += ballot['votes']
                        continue

                    add_second_choice(ballot, index, second_choices)

                # summ all second choices into num_ballots
                num_ballots = sum(second_choices.values())

                # the transferable value to each ballot is calculated
                if num_ballots > 0:
                    transfer_factor = float(transferred) / num_ballots
                    iteration['exhausted']['transferred'] = exhausted
                else:
                    iteration['exhausted']['transferred'] = transferred

                # and we then transfer those values to the answers
                for key, value in second_choices.iteritems():
                    iteration['answers'][key]['received'] += value * transfer_factor

                # recalculate_appointed_seats taking received and transfered into account
                recalculate_appointed_seats(iteration)

                # mark this seat as processed
                processed_seat_ids.append(seat_id)

                # if the goal of appointed number of seats is reached, then we
                # have finished here
                if self.appointed_seats >= self.num_seats:
                    break

        def find_minor_candidate(iteration):
            '''
            Choose *randomly* a candidate which has a count equal to the
            minor candidate count
            '''
            candidates = []
            for key, value in iteration['answers'].iteritems():
                if  effective_count(value) == minor_answer_count:
                    candidates.append(key)

            if len(candidates) == 1:
                return candidates[0]
            elif len(candidates) > 1:
                return candidates[random.randint(0, len(candidates) - 1)]
            else:
                # no minor candidate: i.e. empty election
                return -1

        def remove_minor_candidate(minor_candidate, iteration):
            '''
            Removes the minor candidate from the list of ballots, removing
            also exhausted ballots.
            '''
            minor_candidate_id = self.answer2id(minor_candidate)
            iteration['answers'][minor_candidate]['status'] = 'eliminated'
            def filter_func(ballot):
                # remove the minor candidate from the choices
                ballot['answers'][:] = itertools.ifilter(
                    lambda a: a != minor_candidate_id, ballot['answers'])

                # filterout the ballot if it's exhausted
                continues = len(ballot['answers']) > 0
                if not continues:
                    iteration['exhausted']['votes'] += ballot['votes']
                return continues

            self.ballots[:] = itertools.ifilter(filter_func, self.ballots)

        # Main loop: we iterate until we have an iteration that successfully
        # appoints all seats
        while self.appointed_seats < self.num_seats or force_iteration:
            total_votes = 0
            force_iteration = False

            # create the iteration log object (all_answers is part of it)
            all_answers = dict([(a, dict(votes=0, received=0, transferred=0, status='contesting'))
                for a in self.answer_to_ids_dict.keys()])

            count_first_choice_votes(all_answers)

            iteration = {
                'answers': all_answers,
                'exhausted': {
                    'votes': 0,
                    'transferred': 0
                },
                'quota': 0
            }
            recalculate_quota(iteration)
            recalculate_appointed_seats(iteration)

            if self.appointed_seats == self.num_seats:
                self.iterations.append(iteration)
                break

            transfer_surplus(iteration)

            if self.appointed_seats == self.num_seats:
                self.iterations.append(iteration)
                break

            # if we appointed more seats than needed then we got a bad
            # situation, that we will try to solve by removing one option at a
            # time and iterating again
            if self.appointed_seats > self.num_seats:
                force_iteration = True

            # all valid votes are null, no candidate can be elected
            minor_candidate = find_minor_candidate(iteration)

            # check for empty election
            if minor_candidate != -1:
                remove_minor_candidate(minor_candidate, iteration)

            self.iterations.append(iteration)

            # on empty election, finish
            if minor_candidate == -1:
                break

        # get the resulting data from the last iteration
        last_iteration = self.iterations[-1]
        global_count = sum([answer['total_count'] for answer in result[0]['answers']])

        # fill result
        for answer in result[0]['answers']:
            name = answer['value']
            it_answer = iteration['answers'][name]
            answer['total_count'] = effective_count(it_answer)
            answer['elected'] = (it_answer['status'] == 'elected')

            if answer['elected']:
                pair = (name, self.answer2id(name))
                answer['seat_number'] = 1 + self.appointed_seats_list.index(pair)
            else:
                answer['seat_number'] = 0

        global_count = sum([answer['total_count'] for answer in result[0]['answers']])
        if self.total_number_of_ballots > 0:
            for answer in result[0]['answers']:
                answer['total_count_percentage'] = float(answer['total_count']) / global_count

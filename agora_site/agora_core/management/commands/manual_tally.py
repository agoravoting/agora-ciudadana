# Copyright (C) 2013 Eduardo Robles Elvira <edulix AT wadobo DOT com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from agora_site.misc.utils import *
from agora_site.agora_core.models.voting_systems.base import get_voting_system_by_id

from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
import codecs
import tarfile
import json
import os
from tempfile import mkdtemp

class Command(BaseCommand):
    '''
    Creates the votes file for an encrypted file
    '''

    args = '<n>'
    help = 'Adds n test users'

    def handle(self, *args, **options):
        try:
            tally_path = args[0]
            questions_path = args[1]
        except:
            raise CommandError("usage: <tally_path> <questions_path>")

        if not os.path.exists(tally_path) or not os.path.exists(questions_path):
            raise CommandError("tally path and/or questions_path don't exist")

        with codecs.open(questions_path, encoding='utf-8', mode='r') as qfile:
            questions_content = qfile.read()

        questions = json.loads(questions_content.strip())
        now = timezone.now()

        dir_path = mkdtemp("tally")

        # untar the plaintexts
        tally_gz = tarfile.open(tally_path, mode="r:gz")
        paths = tally_gz.getnames()
        plaintexts_paths = [path for path in paths if path.endswith("/plaintexts_json")]

        i = 0
        for plaintexts_path in plaintexts_paths:
            member = tally_gz.getmember(plaintexts_path)
            member.name = "%d_plaintexts_json" % i
            tally_gz.extract(member, path=dir_path)
            i += 1

        def do_tally(tally_path, dir_path, questions):
            import copy
            # result is in the same format as get_result_pretty(). Initialized here
            result = copy.deepcopy(questions)
            base_vote =[dict(choices=[]) for q in result]

            # setup the initial data common to all voting system
            i = 0
            tallies = []
            for question in result:
                tally_type = question['tally_type']
                voting_system = get_voting_system_by_id(tally_type)
                tally = voting_system.create_tally(None, i)
                tallies.append(tally)

                question['a'] = "question/result/" + voting_system.get_id()
                question['winners'] = []
                question['total_votes'] = 0

                for answer in question['answers']:
                    answer['a'] = "answer/result/" + voting_system.get_id()
                    answer['total_count'] = 0
                    answer['total_count_percentage'] = 0

                tally.pre_tally(result)

                plaintexts_path = os.path.join(dir_path, "%d_plaintexts_json" % i)
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
                            option_index = int(line[1:-2]) - 1
                            if option_index < len(question['answers']):
                                option_str = question['answers'][option_index]['value']

                            # craft the voter_answers in the format admitted by
                            # tally.add_vote
                            voter_answers[i]['choices'] = [option_str]
                        except:
                            print "invalid vote: " + line
                            print "voter_answers = " + json.dumps(voter_answers)
                            import traceback; print traceback.format_exc()

                        tally.add_vote(voter_answers=voter_answers,
                            result=result, is_delegated=False)

                i += 1


            extra_data = dict()

            # post process the tally
            for tally in tallies:
                tally.post_tally(result)

            print json.dumps(dict(
                a= "result",
                counts = result,
                total_votes = result[0]['total_votes'] + result[0]['dirty_votes'],
                total_delegated_votes = 0
            ), indent=4)

        do_tally(tally_path, dir_path, questions)

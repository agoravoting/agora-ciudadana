from openstv.plugins import ReportPlugin

class JsonReport(ReportPlugin):
    "Return a JSON report."

    status = 0
    reportName = "JSON"
    json = {}

    def __init__(self, e):
        self.json = {}
        ReportPlugin.__init__(self, e, None, False)

    def generateReportNonIterative(self):

        self.json['winners'] = [self.cleanB.names[winner] for winner in self.e.winners]
        self.json['num_seats'] = self.e.numSeats
        self.json['candidates'] = self.cleanB.names
        self.json['dirty_ballots_count'] = self.dirtyB.numBallots
        self.json['ballots_count'] = self.cleanB.numBallots
        self.json['answers'] = {}

        i = 0
        for count in self.e.count:
            key = self.cleanB.names[i].decode('utf-8')
            self.json['answers'][key] = count
            i += 1

    def generateReportIterative(self):
        self.json['winners'] = [self.cleanB.names[winner] for winner in self.e.winners]
        self.json['num_seats'] = self.e.numSeats
        self.json['candidates'] = self.cleanB.names
        self.json['dirty_ballots_count'] = self.dirtyB.numBallots
        self.json['ballots_count'] = self.cleanB.numBallots
        self.json['iterations'] = []

        already_won = []
        already_lost = []

        for r in range(self.e.numRounds):
            iteration = {}
            roundStage = r
            if self.e.methodName == "ERS97 STV":
                roundStage = self.e.roundToStage(r)

            index = str(roundStage + 1)
            iteration['round_stage'] = index
            iteration['candidates'] = []

            won = [c for c in range(self.e.b.numCandidates)
                    if self.e.wonAtRound[c] == r]
            won.sort()
            already_won += won

            lost = []
            if (r < self.e.numRounds - 1) and self.e.roundInfo[r+1]["action"][0] == "eliminate":
                lost = self.e.roundInfo[r+1]["action"][1]
                lost.sort()
            already_lost += lost

            xfer = []
            if (r < self.e.numRounds - 1) and self.e.roundInfo[r+1]["action"][0] == "surplus":
                xfer = self.e.roundInfo[r+1]["action"][1]
                xfer.sort()

            def get_status(i):
                if i in won:
                    return 'won'
                elif i in lost:
                    return 'lost'
                elif i in already_won:
                    return 'already_won'
                elif i in already_lost:
                    return 'already_lost'
                else:
                    return 'contesting'

            def get_transfer(i):
                if i in xfer:
                    return True
                else:
                    return False

            for i in xrange(self.e.b.numCandidates):
                x = self.e.count[r][i]
                candidate = {
                    'count': self.e.displayValue(x),
                    'name': self.cleanB.names[i],
                    'status':get_status(i),
                    'transfer': get_transfer(i)
                }
                iteration['candidates'].append(candidate)

            iteration['exhausted'] = self.e.displayValue(self.e.exhausted[r])
            self.json['iterations'].append(iteration)


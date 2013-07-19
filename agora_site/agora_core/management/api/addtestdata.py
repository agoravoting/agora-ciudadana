import sys, getopt
import simplejson as json
import requests
import time
from random import randrange
import random

'''
	Creates an agora (public voting), elections and random delegated and direct votes for existing users
	
	Users are _not_ added, if you want to add users prior to running this script, use something like
	
	./manage.py addtestusers 10
	
	options
	
	-u admin user to log in with
	-p admin password
	-e elections to create
	-d percentage of direct votes to generate (the rest are delegated)
	
	TODO: adding multiples agoras, not just one
'''
def main(argv):	
	# defaults
	percentage = 25
	elections=1
	user="root"
	password="root"

	try:
		opts, args = getopt.getopt(argv,"he:d:u:p:")
	except getopt.GetoptError:
		print 'test.py -e <elections> -p <direct vote percentage>'
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print 'test.py -p <direct vote percentage>'
			sys.exit()		
		elif opt in ("-d"):
			percentage = int(arg)
		elif opt in ("-e"):
			elections = int(arg)
		elif opt in ("-u"):
			user = arg
		elif opt in ("-p"):
			password = arg
	
	header = {'Accept': 'application/json', 'Content-type': 'application/json'}
	
	# log in
	s = requests.Session()
	payload = {"identification": user, "password": password}	
	r = s.post('http://127.0.0.1:8000/api/v1/user/login/', headers=header, data=json.dumps(payload))	
	if r.status_code != 200:
		print "** log in failed for " + user + ", " + password
		print r.status_code, r.text
		sys.exit()			
	print "logged in " + user + " " + str(r.status_code)
	
	# get the csrftoken
	r = s.get('http://127.0.0.1:8000/')			
	header['X-CSRFToken'] = s.cookies['csrftoken']
	
	# print s.cookies['sessionid']		
	# r = s.get('http://127.0.0.1:8000/api/v1/user/settings/', headers=header)
	# print r.status_code, r.text
	
	# create agora
	payload = {
		"pretty_name": "agora" + str(time.time())[5:],
		"short_description": "some fancy description",
		"is_vote_secret": False
	}	
	r = s.post('http://127.0.0.1:8000/api/v1/agora/', headers=header, data=json.dumps(payload) )
	if r.status_code != 201:
		print "** failed creating agora"
		print r.status_code, r.text
		sys.exit()
	agoraId = str(r.json()['id'])		
	print "created agora " + agoraId + " (" + str(r.status_code) + ")"
	
	# create elections and votes
	for e in range(0, elections):
	
		payload = {"identification": user, "password": password}	
		r = s.post('http://127.0.0.1:8000/api/v1/user/login/', headers=header, data=json.dumps(payload))
				
		choices = [
			{
				'a': 'ballot/answer',
				'url': '',
				'details': '',
				'value': 'foo'
			},
			{
				'a': 'ballot/answer',
				'url': '',
				'details': '',
				'value': 'bar'
			}
		]
		questions = [
		{
			'a': 'ballot/question',
			'tally_type': 'ONE_CHOICE',
			'max': 1,
			'min': 0,
			'question': 'Do you prefer foo or bar?',
			'randomize_answer_order': True,
			'answers': choices
		}]
				
		payload = {
			"action": "create_election",
			"questions": questions,
			"pretty_name": "Yes no or maybe" + str(e),
			"description": "time to choose",
			"is_vote_secret": False
		}		
		
		r = s.post('http://127.0.0.1:8000/api/v1/agora/' + agoraId + '/action/', headers=header, data=json.dumps(payload) )
		if r.status_code != 200:
			print "** could not create election"
			print r.status_code, r.text
			sys.exit()			
				
		electionId = r.json()['id']
		print "created election " + str(electionId) + " (" + str(r.status_code) + ")"
		
		'''payload = {
			"action": "get_permissions"
		}		
		r = s.post('http://127.0.0.1:8000/api/v1/election/' + str(electionId) + '/action/', headers=header, data=json.dumps(payload) )	
		print "permissions " + str(r.text)'''		
		
		payload = {
			"action": "start"
		}	
		r = s.post('http://127.0.0.1:8000/api/v1/election/' + str(electionId) + '/action/', headers=header, data=json.dumps(payload) )	
		if r.status_code != 200:
			print "** could not start election"
			print r.status_code, r.text
			sys.exit()			
		
		print "started election " + str(electionId) + " (" + str(r.status_code) + ")"
		
		# get users
		r = s.get('http://127.0.0.1:8000/api/v1/user/', headers=header, params={'limit': 1000})
		users = r.json()
		
		print "direct vote percentage " + str(percentage) + " users " + str(len(users['objects']))
		lastDirect = int((percentage/100.0) * len(users['objects']))
		print "lastDirect is " + str(lastDirect)
		count = 0
		for i in users['objects']:
			username = i['username']
			userid = i['id']
			loginPayload = {"identification": username, "password": "123"}	
			# root user does not need to join agora
			if(count > 0):
				r = s.post('http://127.0.0.1:8000/api/v1/user/login/', headers=header, data=json.dumps(loginPayload))
				print "logged in " + username + " " + str(r.status_code)
											
				# only need to join the agora once
				if e == 0:
					payload = {"action": "join"}
					r = s.post('http://127.0.0.1:8000/api/v1/agora/' + str(agoraId) + '/action/', headers=header, data=json.dumps(payload) )			
					print "joined agora for " + username + " (" + str(r.status_code) + ")"
			if(count <= lastDirect):				
				choice = random.choice(choices)['value']
				payload = {"action": "vote", "is_vote_secret": False, "question0": choice}
				r = s.post('http://127.0.0.1:8000/api/v1/election/' + str(electionId) + '/action/', headers=header, data=json.dumps(payload) )
				print "direct vote for " + username + " is " + choice + " (" + str(r.status_code) + ")"
			else:
				target = userid
				while target == userid:
					targetIndex = randrange(lastDirect)	
					target = users['objects'][targetIndex]['id']
				payload = {"action": "delegate_vote", "user_id": target}
				r = s.post('http://127.0.0.1:8000/api/v1/agora/' + agoraId + '/action/', headers=header, data=json.dumps(payload) )
				print "delegation from " + username + " to " + str(target) + " (" + str(r.status_code) + ")"
				
			count = count + 1

if __name__ == "__main__":
	main(sys.argv[1:])
all: mainjs agorajs agoraless

dependencies:
	mkdir node_modules
	npm install uglify-js less jshint

agoraless:
	./node_modules/less/bin/lessc \
		./agora_site/static/less/agora.less \
		> ./agora_site/static/less/agora.css

mainjs:
	./node_modules/uglify-js/bin/uglifyjs \
					      agora_site/static/js/libs/jquery-1.8.3.min.js \
					      agora_site/static/js/libs/underscore-min.js \
					      agora_site/static/js/libs/json2.js \
					      agora_site/static/js/libs/backbone-min.js \
					      agora_site/static/js/libs/underscore.string.min.js \
					      agora_site/static/js/libs/bootstrap.min.js \
					      agora_site/static/js/libs/jquery-ui-1.8.23.custom.min.js \
					      agora_site/static/js/libs/jquery-ui-timepicker-addon.js \
					      agora_site/static/js/libs/jquery-shuffle.js \
					      agora_site/static/js/libs/jsrender.js \
					      agora_site/static/js/libs/d3.v2.min.js \
					      agora_site/static/js/libs/moment.min.js \
					      agora_site/static/js/libs/moment-lang/gl.js \
					      agora_site/static/js/libs/moment-lang/es.js \
					      agora_site/static/js/libs/livestamp.min.js \
					      agora_site/static/js/libs/nod.min.js \
					      agora_site/static/js/libs/showdown.js \
					      agora_site/static/js/libs/backbone-associations.min.js \
					      agora_site/static/js/libs/sortElements-jquery.js \
					      	-o agora_site/static/js/min/main.min.js
agorajs:
	./node_modules/uglify-js/bin/uglifyjs \
					      agora_site/static/js/agora/base.js \
					      agora_site/static/js/agora/ajax.js \
					      agora_site/static/js/agora/views/generic.js \
					      agora_site/static/js/agora/views/home_anonymous.js \
					      agora_site/static/js/agora/views/home.js \
					      agora_site/static/js/agora/views/agora.js \
					      agora_site/static/js/agora/views/agora_list.js \
					      agora_site/static/js/agora/views/agora_user_list.js \
					      agora_site/static/js/agora/views/election.js \
					      agora_site/static/js/agora/views/election_list.js \
					      agora_site/static/js/agora/views/search_list.js \
					      agora_site/static/js/agora/views/user.js \
					      agora_site/static/js/agora/views/user_list.js \
					      agora_site/static/js/agora/views/election_form.js \
					      agora_site/static/js/agora/views/voting_booth.js \
					      	-c -o agora_site/static/js/min/agora.min.js

all: mainjs agorajs agoraless

clean:
	rm -rf node_modules ./agora_site/static/less/agora.css \
		agora_site/static/js/min/main.min.js \
		agora_site/static/js/min/main.compat.min.js \
		agora_site/static/js/min/agora.min.js

dependencies:
	if [ ! -d node_modules ]; then mkdir node_modules; fi
	npm install uglify-js less@1.3.3 jshint

agoraless:
	./node_modules/less/bin/lessc \
		./agora_site/static/less/agora.less \
		> ./agora_site/static/less/agora.css

mainjs:
	./node_modules/uglify-js/bin/uglifyjs \
					      agora_site/static/js/libs/jquery.js \
					      agora_site/static/js/libs/underscore.js \
					      agora_site/static/js/libs/json2.js \
					      agora_site/static/js/libs/backbone.js \
					      agora_site/static/js/libs/underscore.string.js \
					      agora_site/static/js/libs/bootstrap.js \
					      agora_site/static/js/libs/jquery-ui.js \
					      agora_site/static/js/libs/jquery-ui-timepicker-addon.js \
					      agora_site/static/js/libs/jquery-shuffle.js \
					      agora_site/static/js/libs/jsrender.js \
					      agora_site/static/js/libs/d3.v3.js \
					      agora_site/static/js/libs/nv.d3.js \
					      agora_site/static/js/libs/moment.js \
					      agora_site/static/js/libs/moment-lang/gl.js \
					      agora_site/static/js/libs/moment-lang/es.js \
					      agora_site/static/js/libs/livestamp.js \
					      agora_site/static/js/libs/nod.js \
					      agora_site/static/js/libs/showdown.js \
					      agora_site/static/js/libs/backbone-associations.js \
					      agora_site/static/js/libs/sortElements-jquery.js \
					      -o agora_site/static/js/min/main.min.js
	./node_modules/uglify-js/bin/uglifyjs \
					      agora_site/static/js/libs/es5-shim.js \
					      agora_site/static/js/libs/jquery.js \
					      agora_site/static/js/libs/underscore.js \
					      agora_site/static/js/libs/json2.js \
					      agora_site/static/js/libs/backbone.js \
					      agora_site/static/js/libs/underscore.string.js \
					      agora_site/static/js/libs/bootstrap.js \
					      agora_site/static/js/libs/jquery-ui.js \
					      agora_site/static/js/libs/jquery-ui-timepicker-addon.js \
					      agora_site/static/js/libs/jquery-shuffle.js \
					      agora_site/static/js/libs/jsrender.js \
					      agora_site/static/js/libs/r2d3.js \
					      agora_site/static/js/libs/nv.d3.js \
					      agora_site/static/js/libs/moment.js \
					      agora_site/static/js/libs/moment-lang/gl.js \
					      agora_site/static/js/libs/moment-lang/es.js \
					      agora_site/static/js/libs/livestamp.js \
					      agora_site/static/js/libs/nod.js \
					      agora_site/static/js/libs/showdown.js \
					      agora_site/static/js/libs/backbone-associations.js \
					      agora_site/static/js/libs/sortElements-jquery.js \
					      -o agora_site/static/js/min/main.compat.min.js -b
agorajs:
	./node_modules/uglify-js/bin/uglifyjs \
					      agora_site/static/js/agora/base.js \
					      agora_site/static/js/agora/ajax.js \
					      agora_site/static/js/agora/libs/charts.js \
					      agora_site/static/js/agora/views/generic.js \
					      agora_site/static/js/agora/views/home_anonymous.js \
					      agora_site/static/js/agora/views/user_agora_list.js \
					      agora_site/static/js/agora/views/home.js \
					      agora_site/static/js/agora/views/agora.js \
					      agora_site/static/js/agora/views/available_authorities.js \
					      agora_site/static/js/agora/views/agora_list.js \
					      agora_site/static/js/agora/views/agora_settings.js \
					      agora_site/static/js/agora/views/agora_user_list.js \
					      agora_site/static/js/agora/views/election.js \
					      agora_site/static/js/agora/views/election_list.js \
					      agora_site/static/js/agora/views/search_list.js \
					      agora_site/static/js/agora/views/user.js \
					      agora_site/static/js/agora/views/user_settings.js \
					      agora_site/static/js/agora/views/user_list.js \
					      agora_site/static/js/agora/views/election_form.js \
					      agora_site/static/js/agora/views/voting_booth.js \
					      	-c -o agora_site/static/js/min/agora.min.js

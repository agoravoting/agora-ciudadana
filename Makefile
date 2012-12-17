all:

dependences:
	npm install uglify-js less jshint


mainjs:
	./node_modules/uglify-js/bin/uglifyjs \
					      agora_site/static/js/libs/jquery-1.8.3.min.js \
					      agora_site/static/js/libs/underscore-min.js \
					      agora_site/static/js/libs/json2.js \
					      agora_site/static/js/libs/backbone-min.js \
					      agora_site/static/js/libs/underscore.string.min.js \
					      agora_site/static/js/libs/bootstrap.min.js \
					      agora_site/static/js/libs/handlebars-1.0.rc.1.js \
					      agora_site/static/js/libs/jquery-ui-1.8.23.custom.min.js \
					      agora_site/static/js/libs/jquery-ui-timepicker-addon.js \
					      agora_site/static/js/libs/jquery.timeago.js \
					      agora_site/static/js/libs/jsrender.js \
					      agora_site/static/js/libs/d3.v2.min.js \
					      	-o agora_site/static/js/min/main.min.js

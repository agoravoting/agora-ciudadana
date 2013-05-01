var Ajax = Backbone.View.extend({
    initialize: function() {
        _.bindAll(this);
    },

    setContext: function(ctx) {
        this.ctx = ctx;
    },

    get: function(url, data, type) {
        return this.request("GET", url, data, type);
    },

    post: function(url, data, type) {
        return this.request("POST", url, data, type);
    },

    put: function(url, data, type) {
        return this.request("PUT", url, data, type);
    },

    delete: function(url, data, type) {
        return this.request("DELETE", url, data, type);
    },

    request: function(type, url, data, dataType) {
        var ajax_data = {
            url: url,
            dataType: dataType || "text",
            type: type
        };

        if (data !== undefined) {
            ajax_data.data = data;
        }

        if (this.options.contentType) {
            ajax_data.contentType = this.options.contentType;
        }

        if (this.options.headers) {
            ajax_data.headers = this.options.headers;
        }

        ajax_data.complete = this.requestComplete;
        return $.ajax(ajax_data);
    },

    requestComplete: function(jxhr, stat) {
        this.trigger('success', jxhr, stat, this.ctx);
    }
});

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie != '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                        var cookie = jQuery.trim(cookies[i]);
                        // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
            // Only send the token to relative URLs i.e. locally.
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});

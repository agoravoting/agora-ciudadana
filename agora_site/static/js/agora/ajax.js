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

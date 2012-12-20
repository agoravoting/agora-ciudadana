(function() {
    var Agora = this.Agora,
        app = this.app;

    /*
     * View for search pages.
    */
    (function() {
        var SearchInfiniteView = Agora.GenericListView.extend({
            el: "#activity-list",
            templateEl: "#template-search-item",
            initialize: function() {
                this.params = {q: this.$el.data('query')};
                Agora.GenericListView.prototype.initialize.apply(this);
            },
            renderItem: function(model) {
                var templateEl = this.templateEl;
                var ctype = model.get('obj').content_type;
                console.log("CTYPE: " + ctype);
                if (ctype === "agora") {
                    templateEl = "#template-search-agora-item";
                } else if (ctype === "election") {
                    templateEl = "#template-search-election-item";
                } else if (ctype === "profile") {
                    templateEl = "#template-search-profile-item";
                }
                var template = _.template($(templateEl).html());
                var ret = template(model.toJSON().obj);
                return ret;
            },
        });

        Agora.SearchListView = Backbone.View.extend({
            el: "div.search",

            initialize: function() {
                _.bindAll(this);
                this.infiniteListView = new SearchInfiniteView();
            }
        });
    }).call(this);
}).call(this);

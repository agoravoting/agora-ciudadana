(function() {
    var AgoraInfiniteView = Agora.GenericListView.extend({
        el: "#activity-list",
        templateEl: "#template-search-agora-item",

        setup: function() {
            this.converter = new Showdown.converter();
            Agora.GenericListView.prototype.setup.apply(this);
        },

        renderItem: function(model) {
            var json = model.toJSON();
            json.short_description = this.converter.makeHtml(json.short_description);
            return this.template(json);
        }
    });

    Agora.AgoraListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new AgoraInfiniteView();
        }
    });
}).call(this);

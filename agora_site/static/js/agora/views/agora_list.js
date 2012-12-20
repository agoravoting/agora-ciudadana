(function() {
    var AgoraListView = Agora.GenericListView.extend({
        el: "#activity-list",
        templateEl: "#template-search-agora-item"
    });

    Agora.AgoraListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new AgoraListView();
        }
    });
}).call(this);
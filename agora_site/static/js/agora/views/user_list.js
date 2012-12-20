(function() {
    var UserListView = Agora.GenericListView.extend({
        el: "#activity-list",
        templateEl: "#template-search-profile-item"
    });

    Agora.AgoraListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new UserListView();
        }
    });
}).call(this);
(function() {
    var UserInfiniteView = Agora.GenericListView.extend({
        el: "#activity-list",
        templateEl: "#template-search-profile-item"
    });

    Agora.UserListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new UserInfiniteView();
        }
    });
}).call(this);
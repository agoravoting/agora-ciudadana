(function() {
    var UserInfiniteView = Agora.GenericListView.extend({
        el: "#user-list",
        templateEl: "#template-search-profile-item",

        renderItem: function(model) {
            var json = model.toJSON()
            json.initials = Agora.getUserInitials(json);
            return this.template(json);
        },
    });

    Agora.UserListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new UserInfiniteView();
        }
    });
}).call(this);
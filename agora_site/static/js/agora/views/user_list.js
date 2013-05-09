(function() {
    var UserInfiniteView = Agora.GenericListView.extend({
        el: "#user-list",
        templateEl: "#template-search-profile-item",

        renderItem: function(model) {
            var json = model.toJSON()
            json.initials = this.getInitials(json);
            return this.template(json);
        },

        getInitials: function(json) {
            if (json.full_name && json.full_name != json.username) {
                var initials = "";
                var words = json.full_name.trim().split(" ");
                _.each(words, function (word) {
                    initials += word[0].toUpperCase();
                });
                return initials;
            } else {
                return json.username[0].toUpperCase();
            }
        }
    });

    Agora.UserListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new UserInfiniteView();
        }
    });
}).call(this);
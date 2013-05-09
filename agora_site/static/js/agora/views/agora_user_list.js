(function() {
    var AgoraUserInfiniteView = Agora.GenericListView.extend({
        el: "#user-list",
        templateEl: "#template-agora-profile-item",

        events: {
            'click .user-result .row': 'clickUser',
        },

        renderItem: function(model) {
            var json = model.toJSON();
            json.agora_id = this.$el.data('agora-id');
            json.agora_path = this.$el.data('agora-path');
            json.initials = this.getInitials(json);
            return this.template(json);
        },

        getInitials: function(json) {
            if (json.full_name && json.full_name != json.username) {
                var initials = "";
                var words = json.full_name.split(" ");
                _.each(words, function (word) {
                    initials += word[0].toUpperCase();
                });
                return initials;
            } else {
                return json.username[0].toUpperCase();
            }
        },

        clickUser: function(e) {
            if ($(e.target).closest("a")) {
                return;
            }
            var url = $(e.target).closest(".row").data('url');
            window.location.href= url;
        }
    });

    Agora.AgoraUserListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new AgoraUserInfiniteView();
        }
    });
}).call(this);
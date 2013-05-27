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
            json.initials = Agora.getUserInitials(json);
            return this.template(json);
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

            app.addMembersDialog = new Agora.ModalDialogView();
            title = gettext('Add members manually');
            var body = _.template($("#template-add_members_modal_dialog_body").html())();
            var footer = _.template($("#template-add_members_modal_dialog_footer").html())();

            app.addMembersDialog.populate(title, body, footer);
            $("#manual-member").click(function() {
                app.addMembersDialog.show();
                return false;
            });
        }
    });
}).call(this);
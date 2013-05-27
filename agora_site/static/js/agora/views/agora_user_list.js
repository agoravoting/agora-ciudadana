(function() {
    var AgoraUserInfiniteView = Agora.GenericListView.extend({
        el: "#user-list",
        templateEl: "#template-agora-profile-item",

        events: {
            'click .user-result .row': 'clickUser',
            'click .action-send-message': 'showSendMessageDialog'
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
        },

        showSendMessageDialog: function(e) {
            e.preventDefault();

            $(e.target).closest('.dropdown').find('.dropdown-toggle').dropdown('toggle');
            var user_id = $(e.target).closest("div.row.bottom-bordered").data('id');
            var user_fullname = $(e.target).closest("div.row.bottom-bordered").data('fullname');

            app.sendMessageDialog = new Agora.ModalDialogView();
            var title = interpolate(gettext('Send a message to %s'), [user_fullname]);

            var data = {"user_fullname": user_fullname};
            var body = _.template($("#template-send_mail_modal_dialog_body").html())(data);
            var footer = _.template($("#template-send_mail_modal_dialog_footer").html())();

            app.sendMessageDialog.populate(title, body, footer);
            app.sendMessageDialog.show();
            $('#send-mail-action').click(function (e) {
                e.preventDefault();
                if ($("#send-mail-action").hasClass("disabled")) {
                    return;
                }
                $("#send-mail-action").addClass("disabled");

                var json = {
                    "comment": $("#mail_content").val()
                };

                var jqxhr = $.ajax("/api/v1/user/" + user_id + "/send_mail/", {
                    data: JSON.stringifyCompat(json),
                    contentType : 'application/json',
                    type: 'POST',
                })
                .done(function() {
                    $("#modal_dialog").modal('hide');
                    alert(gettext("Mail sent successfully"));
                })
                .fail(function() {
                    $("#send-mail-action").removeClass("disabled");
                    alert(gettext("Error sending the message, please try again later"));
                });
            });

            return false;
        }
    });

    Agora.AgoraUserListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new AgoraUserInfiniteView();

            app.addMembersDialog = new Agora.ModalDialogView();
            var title = gettext('Add members manually');
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
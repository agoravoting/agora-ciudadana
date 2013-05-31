(function() {
    var AgoraUserInfiniteView = Agora.GenericListView.extend({
        el: "#user-list",
        templateEl: "#template-agora-profile-item",

        events: {
            'click .user-result .row': 'clickUser',
            'click .action-send-message': 'showSendMessageDialog',
            'click .action-choose-as-delegate': 'delegateVote'
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

        delegateVote: function (e) {
            e.preventDefault();
            var id = this.$el.data('agora-id');
            var voter = this.collection.get(id).toJSON();

            $(e.target).closest(".action-choose-as-delegate").data("agora", ajax_data.agora);
            $(e.target).closest(".action-choose-as-delegate").data("delegate", voter);

            Agora.delegateVoteHandler(e, this);
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

                return false;
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
            $("#manual-member").click(function() {
                var title = gettext('Add members manually');
                var body = _.template($("#template-add_members_modal_dialog_body").html())();
                var footer = _.template($("#template-add_members_modal_dialog_footer").html())();

                app.addMembersDialog.populate(title, body, footer);
                app.addMembersDialog.show();

                $("#add-members-action").click(function(e) {
                    e.preventDefault();
                    if ($("#add-members-action").hasClass("disabled")) {
                        return false;
                    }
                    var json = {
                        agoraid: ajax_data.agora.id,
                        emails: $("#add_members_textarea").val(),
                        welcome_message: gettext('Welcome to this agora')
                    }

                    if (json.emails.length == 0) {
                        return false;
                    }

                    json.emails = json.emails.split(",");

                    $("#add-members-action").addClass("disabled");

                    var jqxhr = $.ajax("/api/v1/user/invite/", {
                        data: JSON.stringifyCompat(json),
                        contentType : 'application/json',
                        type: 'POST',
                    })
                    .done(function() {
                        $("#modal_dialog").modal('hide');
                    })
                    .fail(function() {
                        $("#add-members-action").removeClass("disabled");
                        alert(gettext("Error sending the invitations, please check the input data"));
                    });
                    return false;
                });

                return false;
            });
        }
    });
}).call(this);

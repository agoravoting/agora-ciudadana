(function() {
    var AgoraUserInfiniteView = Agora.GenericListView.extend({
        el: "#user-list",
        templateEl: "#template-agora-profile-item",

        events: {
            'click .user-result .row': 'clickUser',
            'click .action-send-message': 'showSendMessageDialog',
            'click .action-choose-as-delegate': 'delegateVote',
            'click .dropdown-toggle': 'toggleDropdown'
        },

        filter: function(param) {
            if (!param) {
                this.url = this.$el.data('url');
            } else {
                this.url = this.$el.data('url') + "?username=" + param;
            }
            this.collection.reset();

            this.firstLoadSuccess = false;
            this.finished = false;
            this.offset = 0;
            this.requestObjects();
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

        toggleDropdown: function(e) {
            // load user permissions
            console.log("dropdown event");
            var dropdown = $(e.target).closest('.dropdown-toggle');
            if (dropdown.data("permissions")) {
                return;
            }
            var json = {
                'action': 'get_permissions',
                'userid': dropdown.closest('.row').data('id')
            };
            var self = this;
            var jqxhr = $.ajax("/api/v1/agora/" + ajax_data.agora.id + "/action/", {
                    data: JSON.stringifyCompat(json),
                    contentType : 'application/json',
                    type: 'POST',
                })
                .done(function(data) {
                    data.agora_path = self.$el.data('agora-path');
                    data.username = dropdown.closest('.row').data('username');
                    data.id = dropdown.closest('.row').data('id');
                    dropdown.data("permissions", data);
                    var templatePerms = _.template($("#template-agora-profile-permissions").html());
                    dropdown.closest('.dropdown-toggle').next().html(
                        templatePerms(data)
                    );
                });
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
            if (!user_fullname.length) {
                user_fullname = $(e.target).closest("div.row.bottom-bordered").data('username');
            }

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
            this.agoraActionListView = new Agora.AgoraActionListView();
            app.modalDialog = new Agora.ModalDialogView();

            this.filter = '';
            var obj = this;

            var delay = (function(){
              var timer = 0;
              return function(callback, ms){
                clearTimeout (timer);
                timer = setTimeout(callback, ms);
              };
            })();
            $("#filter-input").keyup(function(e) {
                delay(function() {
                    obj.filterList();
                }, 500);
            });
            $("#filter-input").keypress(function(e) {
                if(e.which == 13) {
                    obj.filterList();
                }
            });
            $("#filter-button").click(function() {
                obj.filterList();
            });
        },

        filterList: function() {
            newf = $("#filter-input").val();
            if (this.filter != newf) {
                this.filter = newf;
                this.infiniteListView.filter(this.filter);
            }
        }
    });
}).call(this);

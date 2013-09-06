(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.TalliedElectionsView = Backbone.View.extend({
        el: "#tallied_elections_view",

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-tallied_elections_view").html());
            this.render();

            return this.$el;
        },

        render: function() {
            // preprocess ajax_data for the template

            // for each eleciton
            for (var i = 0; i < ajax_data.tallied_elections.objects.length; i++) {
                var election = ajax_data.tallied_elections.objects[i];
                election.result.is_simple = false;

                election.result.participation_percentage = 
                    Agora.round2decimals(election.result.total_votes * 100.0 / election.result.electorate_count);

                // in simple elections, find the winner data
                if (election.result.counts.length == 1 &&
                    election.result.counts[0].a == "question/result/ONE_CHOICE") {
                    var winner = election.result.counts[0].winners[0];
                    var answers = election.result.counts[0].answers;
                    for (var j = 0; j < answers.length; j++) {
                        if (answers[j].value == winner) {
                            election.result.winner_data = answers[j];
                            election.result.winner_data.total_count_percentage =
                                Agora.round2decimals(
                                    election.result.winner_data.total_count_percentage);
                            election.result.is_simple = true;
                            break;
                        }
                    }
                }
            }

            // render template
            this.$el.html(this.template(ajax_data.tallied_elections));
            this.delegateEvents();
            return this;
        },
    });

    Agora.AgoraActionListView = Agora.ActionListView.extend({
        sendingData: false,

        setup: function() {
            this.model = {
                dropdown: false,
                main_action_class: "btn-success",
                main_action_icon: "icon-heart icon-white",
                main_action_name: gettext("Join this agora now"),
                main_action_id: "join",
                actions: []
            };

            var userid = $("body").data("userid");
            if (ajax_data.agora.creator.id == userid ||
                _.contains(ajax_data.user_permissions.permissions, "admin") ||
                _.contains(ajax_data.user_permissions.permissions, "leave")) {
                this.model.main_action_icon = "icon-cog";
                this.model.dropdown =  true;
                this.model.main_action_class = "";
                this.model.main_action_id = "";
                this.model.main_action_name = gettext("Quick actions");
            }

            if (_.contains(ajax_data.user_permissions.permissions, "admin")) {
                this.model.actions = this.model.actions.concat([
                    {
                        id: "admin-agora",
                        name: gettext("Edit agora details"),
                        icon: "icon-edit"
                    },
                    {
                        id: "add-members-manually",
                        name: gettext("Add members manually.."),
                        icon: "icon-plus"
                    },
                    {
                        id: "send-email-to-members",
                        name: gettext("Send email to members.."),
                        icon: "icon-envelope"
                    },
                    {
                        id: "remove-my-admin-membership",
                        name: gettext("Remove my admin membership"),
                        icon: "icon-remove"
                    }
                ]);
            }

            if (_.contains(ajax_data.user_permissions.permissions, "leave")) {
                this.model.actions = this.model.actions.concat([
                    {
                        id: "leave-agora",
                        name: gettext("Leave this agora"),
                        icon: "icon-remove"
                    }
                ]);
            }

            if (_.contains(ajax_data.user_permissions.permissions, "request_admin_membership")) {
                this.model.actions.push({
                    id: "request-admin",
                    name: gettext("Request admin membership"),
                    icon: "icon-eject"
                });
            }

            if (_.contains(ajax_data.user_permissions.permissions, "cancel_admin_membership_request")) {
                this.model.actions.push({
                    id: "cancel-admin-request",
                    name: gettext("Cancel admin membership request"),
                    icon: "icon-remove"
                });
            }

            if (_.contains(ajax_data.user_permissions.permissions, "cancel_vote_delegation")) {
                this.model.actions.push({
                    id: "cancel-vote-delegation",
                    name: gettext("Cancel vote delegation"),
                    icon: "icon-remove"
                });
            }

            if (_.contains(ajax_data.user_permissions.permissions, "request_membership")) {
                this.model = {
                    dropdown: false,
                    main_action_class: "btn-success",
                    main_action_icon: "icon-heart icon-white",
                    main_action_name: gettext("Request membership in this agora"),
                    main_action_id: "request-membership",
                    actions: []
                };
            }

            if (_.contains(ajax_data.user_permissions.permissions, "cancel_membership_request")) {
                this.model = {
                    dropdown: false,
                    main_action_class: "",
                    main_action_icon: "icon-remove",
                    main_action_name: gettext("You requested membership"),
                    main_action_id: "cancel-membership-request",
                    actions: []
                };
            }
        },

        doAction: function(e) {
            e.preventDefault();
            if (this.sendingData) {
                return;
            }

            var a = $(e.target).closest("a");
            var action_id = a.data('id');
            if (!action_id) {
                return;
            }

            this.sendingData = true;
            a.addClass("disabled");

            var data = null;
            switch (action_id) {
            case "admin-agora":
                window.location.href = ajax_data.agora.url + "/admin";
                return;
                break;
            case "add-members-manually":
                a.removeClass("disabled");
                this.sendingData = false;

                this.addMembersManually();
                return;
            case "send-email-to-members":
                a.removeClass("disabled");
                this.sendingData = false;

                this.showMailToMembersDialog();
                return;
            case "remove-my-admin-membership":
                data = {action: "leave_admin_membership"};
                break;
            case "leave-agora":
                data = {action: "leave"};
                break;
            case "request-admin":
                data = {action: "request_admin_membership"};
                break;
            case "cancel-admin-request":
                data = {action: "cancel_admin_membership_request"};
                break;
            case "join":
                data = {action: "join"};
                break;
            case "request-membership":
                data = {action: "request_membership"};
                break;
            case "cancel-membership-request":
                data = {action: "cancel_membership_request"};
                break;
            case "cancel-vote-delegation":
                data = {action: "cancel_vote_delegation"};
                break;
            case "join":
                data = {action: "join"};
                break;
            case "request-membership":
                data = {action: "request_membership"};
                break;
            default:
                a.removeClass("disabled");
                return;
            }

            var jqxhr = $.ajax("/api/v1/agora/" + ajax_data.agora.id + "/action/", {
                data: JSON.stringifyCompat(data),
                contentType : 'application/json',
                type: 'POST',
            })
            .done(function(e) {
                location.reload();
            });
        },

        addMembersManually: function() {
            var title = gettext('Add members manually');
            var body = _.template($("#template-add_members_modal_dialog_body").html())();
            var footer = _.template($("#template-add_members_modal_dialog_footer").html())();

            app.modalDialog.populate(title, body, footer);
            app.modalDialog.show();

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
        },

        showMailToMembersDialog: function() {
            var title = gettext('Send email to agora members');
            var body = _.template($("#template-mail_to_members_modal_dialog_body").html())();
            var footer = _.template($("#template-mail_to_members_modal_dialog_footer").html())();

            app.modalDialog.populate(title, body, footer);
            app.modalDialog.show();

            $("#send-mail-action").click(function(e) {
                e.preventDefault();
                if ($("#send-mail-action").hasClass("disabled")) {
                    return false;
                }
                var json = {
                    action: "mail_to_members",
                    receivers: $("#mail_receivers").val(),
                    subject: $("#mail_subject").val(),
                    body: $("#mail_body").val()
                }

                if (json.subject.length == 0 || json.body.length == 0) {
                    return false;
                }

                $("#send-mail-action").addClass("disabled");

                var path = "/api/v1/agora/" + ajax_data.agora.id + "/action/";
                var jqxhr = $.ajax(path, {
                    data: JSON.stringifyCompat(json),
                    contentType : 'application/json',
                    type: 'POST',
                })
                .done(function() {
                    $("#modal_dialog").modal('hide');
                })
                .fail(function() {
                    $("#send-mail-action").removeClass("disabled");
                    alert(gettext("Error sending the mail, please check the input data"));
                });
                return false;
            });

            return false;
        }
    });

    Agora.renderAgoraTabs = function() {
        var tabsTemplate = _.template($("#template-agora-tabs-view").html());
        $("#agora-tabs").html(tabsTemplate(ajax_data));
        $("#agora-tabs [data-tabname=" + current_tab + "]").addClass('active');
    };

    Agora.renderAgoraCalendar = function() {
        var tabsTemplate = _.template($("#template-agora-calendar-view").html());
        $("#agora-calendar").html(tabsTemplate(ajax_data));
    };

    Agora.AgoraView = Backbone.View.extend({
        el: "div.agora",

        initialize: function() {
            _.bindAll(this);

            this.calendarView = new Agora.CalendarWidgetView();
            this.agoraActionListView = new Agora.AgoraActionListView();
            app.modalDialog = new Agora.ModalDialogView();

            Agora.renderAgoraTabs();
            Agora.renderAgoraCalendar();

            var text = $("#agora_short_description").text();
            var converter = new Showdown.converter();
            $("#agora_short_description").html(converter.makeHtml(text));

            // Only initialize on correct section of page exists.
            if ($("#activity-list").length > 0) {
                this.activityListView = new Agora.ActivityListView();
                this.talliedElectionsView = new Agora.TalliedElectionsView();
            }
            this.social();
        },

        social: function() {
            var name = ajax_data.agora.name;
            var desc = ajax_data.agora.short_description;
            var link = encodeURIComponent(location.href);
            var hr = '';
            // twitter
            hr = $("#twittershare").attr('href');
            hr += '?url=' + link;
            hr += '&text=' + encodeURIComponent(name + " / " + desc);
            $("#twittershare").attr('href', hr);
            $("#twittershare").click(function() {
                window.open($(this).attr('href'), 'twitter-share-dialog', 'width=626,height=436');
                return false;
            });

            // facebook
            hr = $("#facebookshare").attr('href');
            hr += '?u=' + link;
            $("#facebookshare").attr('href', hr);
            $("#facebookshare").click(function() {
                window.open($(this).attr('href'), 'facebook-share-dialog', 'width=626,height=436');
                return false;
            });

            // google plus
            hr = $("#googleshare").attr('href');
            hr += '?url=' + link;
            $("#googleshare").attr('href', hr);
            $("#googleshare").click(function() {
                window.open($(this).attr('href'), 'google-share-dialog', 'width=626,height=436');
                return false;
            });

            // identica
            hr = $("#identicashare").attr('href');
            hr += '&status_textarea=' + encodeURIComponent(name + " / " + desc) + link;
            $("#identicashare").attr('href', hr);
            $("#identicashare").click(function() {
                window.open($(this).attr('href'), 'identica-share-dialog', 'width=626,height=436');
                return false;
            });
        }

    });
}).call(this)

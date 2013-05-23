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
                main_action_id: "",
                actions: []
            };

            var userid = $("body").data("userid");
            if (ajax_data.agora.creator.id == userid) {
                this.model.main_action_icon = "iconuser";
                this.model.dropdown =  true;
                this.model.main_action_class = "";
                this.model.main_action_name = gettext("You are the owner");
                this.model.actions = [
                    {
                        id: "admin-agora",
                        name: gettext("Edit agora details"),
                        icon: "icon-edit"
                    }
                ];

            } else if (_.contains(ajax_data.user_permissions.permissions, "admin")) {
                this.model.main_action_icon = "icon-user";
                this.model.dropdown =  true;
                this.model.main_action_class = "";
                this.model.main_action_name = gettext("You are an admin");
                this.model.actions = [
                    {
                        id: "admin-agora",
                        name: gettext("Edit agora details"),
                        icon: "icon-edit"
                    },
                    {
                        id: "remove-my-admin-membership",
                        name: gettext("Remove my admin membership"),
                        icon: "icon-remove"
                    }
                ];

            } else if (_.contains(ajax_data.user_permissions.permissions, "leave")) {
                this.model.main_action_icon = "icon-user";
                this.model.dropdown =  true;
                this.model.main_action_class = "";
                this.model.main_action_name = gettext("You are a member");
                this.model.actions = [
                    {
                        id: "leave-agora",
                        name: gettext("Remove my membership"),
                        icon: "icon-remove"
                    }
                ];

                if (_.contains(ajax_data.user_permissions.permissions, "request_admin_membership")) {
                    this.model.actions[1] = {
                        id: "request-admin",
                        name: gettext("Request admin membership"),
                        icon: "icon-eject"
                    };
                } else if (_.contains(ajax_data.user_permissions.permissions, "cancel_admin_membership_request")) {
                    this.model.actions[1] = {
                        id: "cancel-admin-request",
                        name: gettext("Cancel admin membership request"),
                        icon: "icon-remove"
                    };
                }
            } else if (_.contains(ajax_data.user_permissions.permissions, "join")) {
                this.model = {
                    dropdown: false,
                    main_action_class: "btn-success",
                    main_action_icon: "icon-heart icon-white",
                    main_action_name: gettext("Join this agora now"),
                    main_action_id: "join",
                    actions: []
                };
            } else if (_.contains(ajax_data.user_permissions.permissions, "request_membership")) {
                this.model = {
                    dropdown: false,
                    main_action_class: "btn-success",
                    main_action_icon: "icon-heart icon-white",
                    main_action_name: gettext("Request membership in this agora"),
                    main_action_id: "request-membership",
                    actions: []
                };
            } else if (_.contains(ajax_data.user_permissions.permissions, "cancel_membership_request")) {
                this.model = {
                    dropdown: true,
                    main_action_class: "btn-success",
                    main_action_icon: "icon-user",
                    main_action_name: gettext("You requested membership"),
                    main_action_id: "",
                    actions: [
                        {
                            id: "cancel-membership-request",
                            name: gettext("Cancel membership request"),
                            icon: "icon-remove"
                        }
                    ]
                };
            } else {
                this.model = null;
            }
        },

        doAction: function(e) {
            var a = $(e.target).closest("a");
            if (this.sendingData) {
                return;
            }
            this.sendingData = true;
            a.addClass("disabled");

            e.preventDefault();
            var action_id = a.data('id');
            var data = null;
            switch (action_id) {
            case "admin-agora":
                window.location.href = ajax_data.agora.url + "/admin";
                return;
                break;
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

        doMainAction: function(e) {
            var a = $(e.target).closest("a");
            if (this.sendingData || a.data('toggle') == "dropdown") {
                return;
            }
            this.sendingData = true;
            a.addClass("disabled");

            e.preventDefault();
            var action_id = a.data('id');
            var data = null;
            switch (action_id) {
            case "join":
                data = {action: "join"};
                break;
            case "request-membership":
                data = {action: "request_membership"};
                break;
            case "cancel-membership-request":
                data = {action: "cancel_membership_request"};
                break;
            }
            

            var jqxhr = $.ajax("/api/v1/agora/" + ajax_data.agora.id + "/action/", {
                data: JSON.stringifyCompat(data),
                contentType : 'application/json',
                type: 'POST',
            })
            .done(function(e) {
                location.reload();
            });
        }
    });

    Agora.AgoraView = Backbone.View.extend({
        el: "div.agora",

        initialize: function() {
            _.bindAll(this);

            this.calendarView = new Agora.CalendarWidgetView();
            this.agoraActionListView = new Agora.AgoraActionListView();

            // Only initialize on correct section of page exists.
            if ($("#activity-list").length > 0) {
                this.activityListView = new Agora.ActivityListView();
                this.talliedElectionsView = new Agora.TalliedElectionsView();
            }
        }
    });
}).call(this)

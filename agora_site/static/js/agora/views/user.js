(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.TalliedUserElectionsView = Backbone.View.extend({
        el: "#tallied_user_elections_view",

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-tallied_user_elections_view").html());
            this.render();

            return this.$el;
        },

        render: function() {
            // preprocess ajax_data for the template

            // for each election
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
            var data = ajax_data.tallied_elections;
            data.user = ajax_data.user;
            this.$el.html(this.template(data));
            this.delegateEvents();
            return this;
        },
    });

    Agora.UserView = Backbone.View.extend({
        el: "div.user",

        initialize: function() {
            _.bindAll(this);
            // Only initialize on correct section of page exists.
            if ($("#activity-list").length > 0) {
                this.activityListView = new Agora.ActivityListView();
            }
            this.tallied_user_elections_view = new Agora.TalliedUserElectionsView();
            this.user_agoras_list_view = new Agora.UserAgorasListView();
        }
    });
}).call(this)

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
                    (election.result.electorate_count * 100.0 / election.result.total_votes);
                // round two decimals
                election.result.participation_percentage =
                    Math.round(election.result.participation_percentage * 100) / 100;

                // in simple elections, find the winner data
                if (election.result.counts.length == 1 &&
                    election.result.counts[0].a == "question/result/ONE_CHOICE") {
                    var winner = election.result.counts[0].winners[0];
                    var answers = election.result.counts[0].answers;
                    for (var j = 0; j < answers.length; j++) {
                        if (answers[j].value == winner) {
                            election.result.winner_data = answers[j];
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

    Agora.AgoraView = Backbone.View.extend({
        el: "div.agora",

        initialize: function() {
            _.bindAll(this);

            this.calendarView = new Agora.CalendarWidgetView();

            // Only initialize on correct section of page exists.
            if ($("#activity-list").length > 0) {
                this.activityListView = new Agora.ActivityListView();
                this.talliedElectionsView = new Agora.TalliedElectionsView();
            }
        }
    });
}).call(this)

(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.UserAgorasListView = Backbone.View.extend({
        el: "#user_agora_list",

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-user_agora_list").html());
            this.render();

            return this.$el;
        },

        render: function() {
            var data = ajax_data;
            this.$el.html(this.template(data));
            this.delegateEvents();

            function agoraChartData(agora) {
                var castvotes = ajax_data.castvotes_by_agoras[(agora.id).toString()].objects;
                var abs_values = _.map(castvotes, function(castvote) {
                    return {
                        x: new Date(castvote.created_at_date).getTime(),
                        y: castvote.count
                    };
                });
                abs_values = _.sortBy(abs_values, function (item) {return item.x });

                return [
                    {
                        values: abs_values,
                        key: gettext("Delegated votes"),
                        color: '#ff7f0e'
                    }
                ]
            }

            for (var i = 0; i < data.user_agoras.objects.length; i++) {
                (function() {
                    var agora = data.user_agoras.objects[i];
                    var chartDivSelector = '#chart-user-agora' + agora.id;
                    var agoraData = agoraChartData(agora);
                    if (agoraData[0].values.length == 0) {
                        return;
                    }
                    nv.addGraph(function() {
                        var chart = nv.models.lineChart();

                        chart.xAxis
//                             .showMaxMin(false)
                            .tickFormat(function(d) {
                                return d3.time.format('%d/%m')(new Date(d));
                            })
                            ;

                        chart.yAxis
                            .tickFormat(d3.format(',f'));

                        d3.select(chartDivSelector + ' svg')
                            .datum(agoraData)
                            .call(chart);

                        $(chartDivSelector).removeClass('hide');
                        chart.update();

                        return chart;
                    });
                })();
            }

            return this;
        }
    });

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

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

            var self = this;
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
                            .ticks(-1)
                            .tickFormat(function(d) {
                                return d3.time.format('%d/%m')(new Date(d));
                            });

                        chart.yAxis
                            .tickFormat(d3.format(',f'));

                        d3.select(chartDivSelector + ' svg')
                            .datum(agoraData)
                            .call(chart);

                        $(chartDivSelector).removeClass('hide');
                        self.$('.agora-user-item[data-agora-id='+ agora.id + ']').removeClass('simple');
                        self.$('.agora-user-item[data-agora-id='+ agora.id + ']').addClass('complex');
                        chart.update();

                        return chart;
                    });
                })();
            }

            return this;
        }
    });
}).call(this)

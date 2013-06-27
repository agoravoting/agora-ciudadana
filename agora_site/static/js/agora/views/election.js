(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.QuestionListView = Backbone.View.extend({
        tagName: "div",
        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-question_list_view").html());
            this.render();
            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(ajax_data));
            $("#question-list").append(this.$el);
            $("#question-list table tbody").each(function (index) {
                var randomize = $(this).data('randomize');
                if (randomize) {
                    $(this).shuffle();
                }
            });
        }
    });

    Agora.ElectionResultsView = Backbone.View.extend({
        tagName: "div",
        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-election_results_view").html());
            this.render();
            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(ajax_data));
            $("#election-results").append(this.$el);
            for (var i = 0; i < ajax_data.election.result.counts.length; i++) {
                var view = null;
                if (ajax_data.election.result.counts[i].tally_type == 'MEEK-STV') {
                    view = new Agora.MeekStvTallyView({
                        question: ajax_data.election.result.counts[i],
                        tally:ajax_data.extra_data.tally_log[i],
                        question_num: i,
                    });
                } else if (ajax_data.election.result.counts[i].tally_type == 'ONE_CHOICE') {
                    view = new Agora.OneChoiceTallyView({
                        question: ajax_data.election.result.counts[i],
                        tally: ajax_data.extra_data.tally_log[i],
                        question_num: i,
                    });
                }
                $("#election-results").append(view.render().el);
            }
        }
    });

    Agora.MeekStvTallyView = Backbone.View.extend({
        tagName: "div",

        id: function() {
            return "tally_question" + this.options.question_num;
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-question_meek_stv_tally").html());
            this.render();
            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.options));
            this.$el.find('tbody tr').sortElements(function (a, b) {
                var rate = function (i) {
                    return ($(i).find('.already_won').length
                        + $(i).find('.won').length
                        - $(i).find('.lost').length
                        - $(i).find('.already_lost').length);
                }
                return rate(a) < rate(b);
            });
            return this;
        },
    });

    Agora.OneChoiceTallyView = Backbone.View.extend({
        tagName: "div",

        id: function() {
            return "tally_question" + this.options.question_num;
        },

        className: "election-results",

        initialize: function() {
            _.bindAll(this);
            this.color = d3.scale.category10();
            this.template = _.template($("#template-question_one_choice_tally").html());
            this.render();
            return this.$el;
        },

        render: function() {
            // render template
            for (var i=0; i<this.options.question.answers.length; i++) {
                this.options.question.answers[i]['color'] = this.color(i);
            }
            this.$el.html(this.template(this.options));
            this.$el.find('li').sortElements(function (a, b) {
                var rate = function (i) {
                    return parseFloat($(i).data('value'));
                }
                return rate(a) < rate(b);
            });
            this.pieChart();
            return this;
        },

        pieChart: function() {
            var pienode = this.$el.find('.piechart')[0];
            Charts.arc(this.options.question.answers,
                       pienode,
                       function (d) { return d.total_count; },
                       function (d) { return d.value; },
                       this.color,
                       500, 250);
        }
    });

    Agora.ElectionView = Backbone.View.extend({
        el: "div.election",

        initialize: function() {
            _.bindAll(this);
            // Only initialize on correct section of page exists.
            if ($("#activity-list").length > 0) {
                this.activityListView = new Agora.ActivityListView();
            }

            this.questionListView = new Agora.QuestionListView();

            if (ajax_data.election.result_tallied_at_date) {
                this.electionResultsView = new Agora.ElectionResultsView();
            }
        }
    });

    Agora.ElectionDelegatesView = Agora.GenericListView.extend({
        el: "#user-list",
        templateEl: "#template-vote_list_item",
        templateVoteInfoEl: "#template-vote_info",
        sendingData: false,

        events: {
            'hover .user-result .row': 'hoverUser'
        },

        initialize: function() {
            Agora.GenericListView.prototype.initialize.apply(this);

            this.delegateView = null;
        },

        renderItem: function(model) {
            return this.template(model.toJSON());
        },

        hoverUser: function(e) {
            if (!this.templateVoteInfoEl) {
                this.templateVoteInfo = _.template($(this.templateVoteInfoEl).html());
            }
            var id = $(e.target).closest('.row').data('id');
            var model = {
                vote: this.collection.get(id).toJSON(),
                election: ajax_data.election,
                extra_data: ajax_data.extra_data
            };
            if (model.election.result_tallied_at_date) {
                model.num_delegated_votes = 0;
                model.rank_in_delegates = "-";
                if (model.vote.delegate_election_count) {
                    model.num_delegated_votes = model.vote.delegate_election_count.count;
                    var rank = model.vote.delegate_election_count.rank;
                    if (rank) {
                        model.rank_in_delegates = rank + "º";
                    }
                }
            }
            $("#vote_info").html(this.templateVoteInfo(model));
            $("#vote_info .delegate_vote").click(this.delegateVote);
        },

        delegateVote: function (e) {
            e.preventDefault();
            Agora.delegateVoteHandler(e, this);
        }
    });
}).call(this)

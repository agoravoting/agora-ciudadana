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
            this.template = _.template($("#template-question_one_choice_tally").html());
            this.render();
            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.options));
            this.$el.find('li').sortElements(function (a, b) {
                var rate = function (i) {
                    return parseFloat($(i).data('value'));
                }
                return rate(a) < rate(b);
            });
            return this;
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

        events: {
            'click .user-result .row': 'clickUser',
            'hover .user-result .row': 'hoverUser',
        },

        renderItem: function(model) {
            return this.template(model.toJSON());
        },

        hoverUser: function(e) {
            if (!this.templateVoteInfo) {
                this.templateVoteInfo = _.template($(this.templateVoteInfoEl).html());
            }
            var id = $(e.target).closest('.row').data('id');
            var model = {
                vote: this.collection.get(id).toJSON(),
                election: ajax_data.election,
                extra_data: ajax_data.extra_data
            };
            if (model.election.result_tallied_at_date) {
                if (ajax_data.extra_data.delegation_counts[model.vote.voter.id]) {
                    model.num_delegated_votes = ajax_data.extra_data.delegation_counts[model.vote.voter.id];
                } else {
                    model.num_delegated_votes = 0;
                }
                var size = _.size(ajax_data.extra_data.delegation_counts);
                var filtered = _.filter(ajax_data.extra_data.delegation_counts,
                    function (val) { return val <= model.num_delegated_votes; }
                );
                model.rank_in_delegates = size - filtered.length + 1;
            }
            $("#vote_info").html(this.templateVoteInfo(model));
        },

        clickUser: function(e) {
//             if ($(e.target).closest("a")) {
//                 return;
//             }
//             var url = $(e.target).closest(".row").data('url');
//             window.location.href= url;
        }
    });
}).call(this)

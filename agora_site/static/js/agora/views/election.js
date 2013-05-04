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
            for (var i = 0; i < ajax_data.election.questions.length; i++) {
                var view = null;
                if (ajax_data.election.questions[i].tally_type == 'MEEK-STV') {
                    view = new Agora.MeekStvTallyView({
                        question: ajax_data.election.questions[i],
                        tally:ajax_data.extra_data.tally_log[i],
                        question_num: i,
                    });
                } else if (ajax_data.questions[i].tally_type == 'ONE_CHOICE') {
                    view = new Agora.OneChoiceTallyView({
                        question: ajax_data.election.questions[i],
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
                    return $(i).find('.already_won').length - $(i).find('.already_lost').length;
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

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-question_one_choice_tally").html());
            this.render();
            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.options));
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
}).call(this)

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

            if (ajax_data.election.tally_released_at_date) {
                this.electionResultsView = new Agora.ElectionResultsView();
            }
        }
    });

    Agora.ElectionDelegatesView = Agora.GenericListView.extend({
        el: "#user-list",
        templateEl: "#template-vote_list_item",
        templateVoteInfoEl: "#template-vote_info",
        templateVoteInfo: null,
        sendingData: false,

        events: {
            'hover .user-result .row': 'hoverUser'
        },

        initialize: function() {
            Agora.GenericListView.prototype.initialize.apply(this);

            this.delegateView = null;
            this.init_filter();
        },

        init_filter: function() {
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
                this.filterf(this.filter);
            }
        },

        filterf: function(param) {
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
            return this.template(model.toJSON());
        },

        hoverUser: function(e) {
            if (!this.templateVoteInfo) {
                this.templateVoteInfo = _.template($(this.templateVoteInfoEl).html());
            }
            var id = $(e.target).closest('.row').data('id');
            var self = this;
            var agora = ajax_data.election.agora;
            self.delegate = (ajax_data.election.agora.delegation_policy == "ALLOW_DELEGATION");
            var model = {
                vote: this.collection.get(id).toJSON(),
                election: ajax_data.election,
                delegation: self.delegate,
                extra_data: ajax_data.extra_data
            };
            if (model.election.tally_released_at_date) {
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
            if(self.delegate == true)
            {
                $("#vote_info .delegate_vote").click(this.delegateVote);
            }
        },

        delegateVote: function (e) {
            e.preventDefault();
            Agora.delegateVoteHandler(e, this);
        }
    });

    Agora.FeaturedElectionView = Backbone.View.extend({
        el: "#content-wrapper",

        initialize: function() {
            _.bindAll(this);
            app.modalDialog = new Agora.ModalDialogView();
            this.bw_template = _.template($("#template_background-wrapper-featured-election").html());
            this.question_template = _.template($("#template_featured-election-question").html());
            this.question_primary_template = _.template($("#template_featured-election-primary-question").html());
            this.oc_question_template = _.template($("#template_featured-election-tallied-one-choice-question").html());
            this.stv_question_template = _.template($("#template_featured-election-tallied-stv-question").html());

            var data = ajax_data;
            data.is_demo = (window.location.href.lastIndexOf("/demo") >= window.location.href.length - 6);

            $("#background-wrapper-fe").html(this.bw_template(ajax_data));
            if (ajax_data.election.tally_released_at_date) {
                for (var i = 0; i < ajax_data.election.questions.length; i++) {
                    var data = {
                        i: i,
                        q: ajax_data.election.result.counts[i],
                        q_tally: ajax_data.extra_data.tally_log[i]
                    };
                    if (data.q.layout == "PRIMARY") {
                        $("#bloques").append(this.question_primary_template(data));
                        $('#q' + i + ' table.question-stv tbody tr').sortElements(function (a, b) {
                            var rate = function (i) {
                                return ($(i).find('.already_won').length
                                    + $(i).find('.won').length
                                    - $(i).find('.lost').length
                                    - $(i).find('.already_lost').length);
                            }
                            return rate(a) < rate(b);
                        });
                        $('.candidates-list.list-' + i + ' .candidate').sortElements(function (a, b) {
                            return $(a).data("pos") > $(b).data("pos");
                        });
                    } else if (data.q.a == "question/result/ONE_CHOICE") {
                        $("#bloques").append(this.oc_question_template(data));
                    } else {
                        var el = this.stv_question_template(data);
                        $("#bloques").append(el);
                        $('#q' + i + ' table.question-stv tbody tr').sortElements(function (a, b) {
                            var rate = function (i) {
                                return ($(i).find('.already_won').length
                                    + $(i).find('.won').length
                                    - $(i).find('.lost').length
                                    - $(i).find('.already_lost').length);
                            }
                            return rate(a) < rate(b);
                        });
                    }
                }
            } else {
                for (var i = 0; i < ajax_data.election.questions.length; i++) {
                    var data = {
                        i: i,
                        q: ajax_data.election.questions[i]
                    };
                    if (data.q.layout == "PRIMARY") {
                        $("#bloques").append(this.question_primary_template(data));

                        // shuffle options
                        if (data.q.randomize_answer_order) {
                            $('.candidates-list.list-' + i).shuffle();
                        }

                    } else {
                        $("#bloques").append(this.question_template(data));
                    }
                }
            }

            // in case there's only on question, uncollapse it
            if (ajax_data.election.questions.length == 1) {
                $("#q0").addClass("in");
            }

            $("a.cand-details").click(this.showDetails);
        },

        showDetails: function(e) {
            e.preventDefault();
            var i = $(e.target).data('question-index');
            var j = $(e.target).data('option-index');
            var answer = ajax_data.election.questions[i].answers[j];

            var title = answer.value;
            var bodyTmpl = _.template($("#template-show_option_details_body").html());
            var body = bodyTmpl(answer);
            var footer = '<button type="button" class="btn btn-warning" data-dismiss="modal" aria-hidden="true">' + gettext("Close") + '</button>';

            app.modalDialog.populate(title, body, footer);
            app.modalDialog.show();
        }
    });


    Agora.ElectionSecurityCenterView = Backbone.View.extend({
        el: "#election-security-center",

        initialize: function() {
            this.template = _.template($("#template-election-security-center").html());
            this.$el.html(this.template(ajax_data));
        }
    });
}).call(this)

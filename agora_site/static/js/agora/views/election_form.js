(function() {
    Agora.ElectionModel = Backbone.Model.extend({});

    Agora.QuestionModel = Backbone.Model.extend({});

    Agora.QuestionEditView = Backbone.View.extend({
        tagName: 'div',

        className: 'tab-pane',
        events: {
            'click .dropdown-menu li a': 'selectVotingSystem',
        },

        id: function() {
            return "question-tab-" + this.model.get('question_num');
        },

        selectVotingSystem: function(e) {
            var id = $(e.target).closest("li").data('id');
            var usertext = $(e.target).closest("li").data('usertext');
            $("#votingsystem").data('id', id);
            $("#votingsystem").html(usertext);
            if (id == "MEEK-STV") {
                $("#num_winners_opts").css('display', 'inline-block');
            } else {
                $("#num_winners_opts").hide();
            }
            this.model.set('tally_type', id);
        },

        initialize: function() {
            this.template = _.template($("#template-election_form_question_tab_pane").html());

            var json = this.model.toJSON();
            this.$el.html(this.template(json));

            // init voting system combo box
            var self = this;
            this.$el.find("#votingsystem-dropdown li").each(function () {
                var id = $(this).data("id");
                if (id == self.$el.find("#votingsystem").data('id')) {
                    var usertext = $(this).data("usertext");
                    self.$el.find("#votingsystem").html(usertext);
                    if (id == "MEEK-STV") {
                        self.$el.find("#num_winners_opts").css('display', 'inline-block');
                    } else {
                        self.$el.find("#num_winners_opts").hide();
                    }
                }
            });
            return this.$el;
        },
    });

    Agora.ElectionCreateForm = Backbone.View.extend({
        el: "div.top-form",

        getMetrics: function() { return [
            ['#pretty_name', 'presence', gettext('This field is required')],
            ['#pretty_name', 'between:4:140', gettext('Must be between 4 and 140 characters long')],

            ['#description', 'presence', gettext('This field is required')],
            ['#description',  'min-length:4', gettext('Must be at least 4 characters long')],

            ['[name=is_vote_secret]',  'presence', gettext('You must choose if vote is secret')],

            ['#start_voting_date', this.checkStartDate, gettext('Invalid date')],
            ['#end_voting_date', this.checkEndDate, gettext('Invalid date')],
        ]},

        events: {
            'click #schedule_voting': 'toggleScheduleVoting',
            'click #show_add_question_tab_btn': 'showAddQuestionTab',
            'click #schedule_voting_label': 'checkSchedule'
        },

        getInitModel: function() {
            return {
                'pretty_name': '',
                'description': '',
                'is_vote_secret': true,
                'questions': [],
            };
        },

        initialize: function() {
            this.template = _.template($("#template-election_form").html());
            this.templateNavtab = _.template($("#template-election_form_question_navtab").html());

            _.bindAll(this);
            this.model = new Agora.ElectionModel(this.getInitModel());

            // render initial template
            this.$el.html(this.template(this.model.toJSON()));

            // add question tab-content
            var add_question_view = new Agora.QuestionEditView({
                model: new Agora.QuestionModel({
                    'a': 'ballot/question',
                    'tally_type': 'ONE_CHOICE',
                    'question_num': 0,
                    'max': 1,
                    'min': 0,
                    'question': 'Do you prefer foo or bar?',
                    'randomize_answer_order': true,
                    'answers': [
                        {
                            'a': 'ballot/answer',
                            'url': '',
                            'details': '',
                            'value': 'fo\"o'
                        },
                        {
                            'a': 'ballot/answer',
                            'url': '',
                            'details': '',
                            'value': 'bar'
                        }
                    ]
                })});
            this.$el.find('.tab-content').append(add_question_view.render().el);

            // populate questions
            this.questionsCollection = new Backbone.Collection([], {
                model: Agora.QuestionModel
            });

            this.listenTo(this.questionsCollection, 'change', this.updateButtonsShown);

            this.questionsCollection.add(this.model.get("questions"));
            this.questionsCollection.each(this.addQuestion);

            this.updateButtonsShown();

            this.$el.find("#create_election_form").nod(this.getMetrics());
            $('.datetimepicker').datetimepicker();

            $("#create_election_form").submit(this.createElection);
        },

        checkSchedule: function(e) {
            if ($("#schedule_voting:checked").length == 0) {
                $(e.target).closest(".error").removeClass('error');
            }
        },

        checkStartDate: function() {
            if ($("#schedule_voting:checked").length == 0) {
                return true;
            }
            var val = this.$el.find("#start_voting_date").val();
            if (!val) {
                return false;
            }
            return isFinite(new Date(val));
        },

        checkEndDate: function() {
            if ($("#schedule_voting:checked").length == 0) {
                return true;
            }
            var val = this.$el.find("#end_voting_date").val();
            if (!val) {
                return true;
            }
            var valid = isFinite(new Date(val));

            var val_start = this.$el.find("#start_voting_date").val();
            return valid && isFinite(new Date(val_start));
        },

        addQuestion: function(questionModel) {
            var i = this.questionsCollection.indexOf(questionModel);
            questionModel.set('question_num', i);
            this.$el.find('#add-question-navtab').append(this.templateNavtab({question_num: i}));

            var view = new Agora.QuestionEditView({model: questionModel});
            this.$el.find('.tab-content').append(view.render().el);
        },

        toggleScheduleVoting: function(e) {
            $('div.top-form #schedule_voting_controls').toggle(e.target.checked);
        },

        createElection: function(e) {
            e.preventDefault();
            // TODO: send election via AJAX, deal with ajax errors, show election on success
            return false;
        },

        updateButtonsShown: function() {
            if (this.questionsCollection.length == 0) {
                this.$el.find("#create_election_btn").hide();
                this.$el.find("#show_add_question_tab_btn").show();
            } else {
                this.$el.find("#create_election_btn").show();
                this.$el.find("show_add_question_tab_btn").hide();
            }
        },

        showAddQuestionTab: function() {
            this.$el.find('.nav-tabs a:last').tab('show');
        }
    });

    Agora.ElectionEditForm = Agora.ElectionCreateForm.extend({
        getInitModel: function() {
            // TODO
        }
    });
}).call(this);

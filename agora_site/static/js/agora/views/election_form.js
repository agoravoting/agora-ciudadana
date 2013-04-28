(function() {
    Agora.AnswerModel = Backbone.AssociatedModel.extend({
        defaults: {
            'a': 'ballot/answer',
            'url': '',
            'details': '',
            'value': ''
        }
    });

    Agora.QuestionModel = Backbone.AssociatedModel.extend({
        relations: [{
            type: Backbone.Many,
            key: 'answers',
            relatedModel: Agora.AnswerModel
        }],
        defaults: {
            'a': 'ballot/question',
            'tally_type': 'ONE_CHOICE',
            'question_num': 0,
            'max': 1,
            'min': 0,
            'question': '',
            'randomize_answer_order': true,
            'answers': []
        }
    });

    Agora.ElectionModel = Backbone.AssociatedModel.extend({
        relations: [{
            type: Backbone.Many,
            key: 'questions',
            relatedModel: Agora.QuestionModel
        }],
        defaults: {
            'pretty_name': '',
            'description': '',
            'is_vote_secret': true,
            'questions': [],
        }
    });

    Agora.AnswerView = Backbone.View.extend({
        tagName: 'tr',

        events: {
            'click td': 'editValue',
            'keyup .input-edit-value': 'keyUpSaveValue'
        },

        initialize: function() {
            _.bindAll(this);
            this.render();

            this.listenTo(this.model, 'destroy', this.remove);
            return this.$el;
        },

        render: function() {
            // render template
            this.template = _.template($("#template-election_form_question_answer").html());
            this.$el.html(this.template(this.model.toJSON()));

            // handle some dom events
            this.$el.find(".input-edit-value").focusout(this.focusOutValue);
            return this;
        },

        editValue: function(e) {
            if (e.target.class == "remove_option") {
                return;
            }
            var val = this.$el.find('.the-value').html();
            this.$el.find('.input-edit-value').val(val);

            this.$el.find('.view-value').hide();
            this.$el.find('.edit-value').show();
            this.$el.find('.input-edit-value').focus();
        },

        keyUpSaveValue: function(e) {
            if (e.keyCode == 13) // <Enter>
            {
                var value = this.$el.find('.input-edit-value').val();
                // check that the value is non empty and not already used
                if (!value) {
                    this.$el.find('.view-value').show();
                    this.$el.find('.edit-value').hide();
                    return;
                }
                // save the value
                this.model.set('value', value);
                this.$el.find('.the-value').html(value)

                this.$el.find('.view-value').show();
                this.$el.find('.edit-value').hide();
            }
            else if (e.keyCode == 27) // <Esc>
            {
                this.$el.find('.view-value').show();
                this.$el.find('.edit-value').hide();
            }
        },

        focusOutValue: function() {
            this.$el.find('.view-value').show();
            this.$el.find('.edit-value').hide();
        }
    });

    Agora.QuestionEditView = Backbone.View.extend({
        tagName: 'div',

        className: 'tab-pane',

        events: {
            'click .dropdown-menu li a': 'selectVotingSystem',
            'click .add_option_btn': 'userAddAnswer',
            'keyup .add_option': 'userAddAnswerEnter',
            'click .remove_option': 'userRemoveAnswer'
        },

        getMetrics: function() {
            var self = this;
            var checkNumWinners = function(val) {
                var num_answers = self.model.get('answers').length;
                if (num_answers < 2) {
                    return true;
                }
                return num_answers > val;
            };

            var checkMax = function(val) {
                var num_answers = self.model.get('answers').length;
                if (num_answers < 2) {
                    return true;
                }
                return num_answers > val;
            };

            var checkMin = function(val) {
                return val >= 0 && val <= self.$el.find('.max_num_choices').val();
            };

            var checkNumAnswers = function(val) {
                var num_answers = self.model.get('answers').length;
                return num_answers >= 2;
            }

            return [
                ['.name', 'presence', gettext('This field is required')],
                ['.name', 'between:4:140', gettext('Must be between 4 and 140 characters long')],
                ['.num_winners', 'presence', gettext('This field is required')],
                ['.min_num_choices', 'presence', gettext('This field is required')],
                ['.max_num_choices', 'presence', gettext('This field is required')],
                ['.num_winners', 'integer', gettext('This field must be an integer')],
                ['.min_num_choices', 'integer', gettext('This field must be an integer')],
                ['.max_num_choices', 'integer', gettext('This field must be an integer')],
                ['.num_winners', checkNumWinners, gettext('Invalid value')],
                ['.min_num_choices', checkMax, gettext('Invalid value')],
                ['.add_option', checkNumAnswers, gettext('Add at least two choices')],
            ];
        },

        id: function() {
            return "question-tab-" + this.model.get('question_num');
        },

        updateModel: function() {
            this.model.set('question', this.$el.find('.name').val());
            this.model.set('num_seats', this.$el.find('.num_winners').val());
            this.model.set('min', this.$el.find('.min_num_choices').val());
            this.model.set('max', this.$el.find('.max_num_choices').val());
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-election_form_question_tab_pane").html());

            this.render();

            this.listenTo(this.model.get("answers"), 'add', this.addAnswer);
            this.listenTo(this.model.get("answers"), 'remove', this.removeAnswer);
            this.listenTo(this.model.get("answers"), 'reset', this.resetAnswers);
            this.listenTo(this.model, 'destroy', this.remove);
            this.listenTo(this.model, 'change:question_num', this.render);
            this.listenTo(this.model.get("answers"), 'change:value', this.answerChanged);

            return this.$el;
        },

        render: function() {
            var json = this.model.toJSON();
            this.$el.html(this.template(json));
            this.$el.attr("id", this.id);

            // init voting system combo box
            var self = this;
            this.$el.find(".votingsystem-dropdown li").each(function () {
                var id = $(this).data("id");
                if (id == self.$el.find(".votingsystem").data('id')) {
                    var usertext = $(this).data("usertext");
                    self.$el.find(".votingsystem").html(usertext);
                    if (id == "MEEK-STV") {
                        self.$el.find(".num_winners_opts").css('display', 'inline-block');
                    } else {
                        self.$el.find(".num_winners_opts").hide();
                    }
                }
            });

            this.resetAnswers();
            this.$el.find("form").nod(this.getMetrics());
            this.$el.find("form").submit(this.createQuestion);
            return this;
        },

        userRemoveAnswer: function(e) {
            var value = $(e.target).closest("a").data('value');
            var model = this.model.get('answers').find(function (answer) {
                return answer.get('value') == value;
            });
            this.model.get('answers').remove(model);
            model.destroy();
        },

        userAddAnswerEnter: function(e) {
            if (e.keyCode == 13) { // <Enter>
                this.userAddAnswer();
                e.preventDefault();
            }
        },

        userAddAnswer: function() {
            var val = this.$el.find(".add_option").val();
            // do not add if text is empty
            if (!val) {
                return;
            }

            // do not add if answer is already listed
            var model = this.model.get('answers').find(function (answer) {
                return answer.get('value') == val;
            });
            if (model) {
                return;
            }

            this.$el.find(".add_option").val('');

           var newAnswer = new Agora.AnswerModel({value: val});
           this.model.get('answers').add(newAnswer);
        },

        addAnswer: function(answerModel) {
            var view = new Agora.AnswerView({model: answerModel});
            this.$el.find('.option-list').append(view.render().el);

            if (this.model.get('answers').length > 0) {
                this.$el.find('.atleastwooptions').hide();
            }
        },

        removeAnswer: function() {
            if (this.model.get('answers').length < 1) {
                this.$el.find('.atleastwooptions').show();
            }
        },

        answerChanged: function(answer) {
            var answers = this.model.get('answers').filter(function (answer2) {
                return answer.get('value') == answer2.get('value');
            });
            if (answers.length > 1) {
                answer.destroy();
            }
        },

        resetAnswers: function() {
            this.$el.find('.option-list').empty();
            this.model.get("answers").each(this.addAnswer);
        },

        resetForm: function() {
            this.stopListening();
            this.model.clear().set(this.model.defaults);
            this.initialize();
        },

        selectVotingSystem: function(e) {
            var id = $(e.target).closest("li").data('id');
            var usertext = $(e.target).closest("li").data('usertext');
            this.$el.find(".votingsystem").data('id', id);
            this.$el.find(".votingsystem").html(usertext);
            if (id == "MEEK-STV") {
                this.$el.find(".num_winners_opts").css('display', 'inline-block');
            } else {
                this.$el.find(".num_winners_opts").val('1');
                this.$el.find(".num_winners_opts").hide();
            }
            this.model.set('tally_type', id);
        },

        createQuestion: function(e) {
            e.preventDefault();
            this.formValid = true;
            return false;
        },
    });

    Agora.ElectionCreateForm = Backbone.View.extend({
        el: "div.top-form",

        getMetrics: function() {
            var self = this;
            var checkStartDate = function() {
                if (self.$el.find("#schedule_voting:checked").length == 0) {
                    return true;
                }
                var val = self.$el.find("#start_voting_date").val();
                if (!val) {
                    return false;
                }
                return isFinite(new Date(val));
            };

            var checkEndDate = function() {
                if (self.$el.find("#schedule_voting:checked").length == 0) {
                    return true;
                }
                var val = self.$el.find("#end_voting_date").val();
                if (!val) {
                    return true;
                }
                var valid = isFinite(new Date(val));

                var val_start = self.$el.find("#start_voting_date").val();
                return valid && isFinite(new Date(val_start));
            };

            return [
                ['#pretty_name', 'presence', gettext('This field is required')],
                ['#pretty_name', 'between:4:140', gettext('Must be between 4 and 140 characters long')],

                ['#description', 'presence', gettext('This field is required')],
                ['#description',  'min-length:4', gettext('Must be at least 4 characters long')],

                ['[name=is_vote_secret]',  'presence', gettext('You must choose if vote is secret')],

                ['#start_voting_date', checkStartDate, gettext('Invalid date')],
                ['#end_voting_date', checkEndDate, gettext('Invalid date')],
            ];
        },

        events: {
            'click #schedule_voting': 'toggleScheduleVoting',
            'click #show_add_question_tab_btn': 'showAddQuestionTab',
            'click #schedule_voting_label': 'checkSchedule',
            'click .create_question_btn': 'createQuestion',
            'click .remove_question_btn': 'removeQuestion',
        },

        getInitModel: function() {
            // ElectionModel contains a default
            return new Agora.ElectionModel();
        },

        initialize: function() {
            this.template = _.template($("#template-election_form").html());
            this.templateNavtab = _.template($("#template-election_form_question_navtab").html());

            _.bindAll(this);
            this.model = this.getInitModel();

            // render initial template
            this.$el.html(this.template(this.model.toJSON()));

            // add question tab-content
            this.addQuestionView = new Agora.QuestionEditView({
                model: new Agora.QuestionModel({'question_num': 0})});
            this.$el.find('.tab-content').append(this.addQuestionView.render().el);

            // load initial models and listen to new ones
            this.listenTo(this.model.get('questions'), 'add', this.addQuestion);
            this.model.get('questions').each(this.addQuestion);

            // update button on model changes and initialize
            this.listenTo(this.model, 'change', this.updateButtonsShown);
            this.listenTo(this.model.get('questions'), 'add', this.updateButtonsShown);
            this.listenTo(this.model.get('questions'), 'remove', this.updateButtonsShown);
            this.updateButtonsShown();

            // do various setup calls
            this.$el.find("#create_election_form").nod(this.getMetrics());
            $('.datetimepicker').datetimepicker();
            $("#create_election_form").submit(this.createElection);
        },

        removeQuestion: function(e) {
            var question_num = $(e.target).data('id');
            var question = this.model.get('questions').at(question_num - 1);
            var length = this.model.get('questions').length;
            question.destroy();
            this.model.get('questions').remove(question);
            this.$el.find("#question-navtab-" + length).remove();

            var i = 1;
            this.model.get('questions').each(function (model) {
                model.set('question_num', i);
                i++;
            }); 

            var selector = "#add-question-navtab a";
            this.$el.find(selector).tab('show');
        },

        createQuestion: function() {
            // use nod to check form is valid. nod will trigger a form submit
            // only if form is valid, which will set this.formValid to true
            this.addQuestionView.formValid = false;
            this.addQuestionView.$el.find("[type=submit]").click();
            if (!this.addQuestionView.formValid) {
                return;
            }

            // create the question
            this.addQuestionView.updateModel();
            var model = this.addQuestionView.model.clone();
            model.set("question_num", this.model.get('questions').length + 1);
            this.model.get('questions').add(model);

            // reset the add question tab
            this.addQuestionView.resetForm();
        },

        checkSchedule: function(e) {
            if ($("#schedule_voting:checked").length == 0) {
                $(e.target).closest(".error").removeClass('error');
            }
        },

        addQuestion: function(questionModel) {
            var i = questionModel.get('question_num');
            this.$el.find('#add-question-navtab').before(this.templateNavtab({question_num: i}));

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
            if (this.model.get("questions").length == 0) {
                this.$el.find("#create_election_btn").hide();
                this.$el.find("#show_add_question_tab_btn").show();
            } else {
                this.$el.find("#create_election_btn").show();
                this.$el.find("#show_add_question_tab_btn").hide();
            }
        },

        showAddQuestionTab: function() {
            this.$el.find('.nav-tabs a:last').tab('show');
        }
    });

    Agora.ElectionEditForm = Agora.ElectionCreateForm.extend({
        getInitModel: function() {
            // TODO
            return {};
        }
    });
}).call(this);

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
            'num_seats': 1,
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
            'security_policy': 'PUBLIC_VOTING',
            'questions': [],
            'from_date': '',
            'to_date': ''
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
            if ($(e.target).hasClass("remove_option")) {
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
            'click .remove_option': 'userRemoveAnswer',
            'click .create_question_btn': 'createQuestion'
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
                ['.name', 'min-length:4', gettext('Must have at least 4 characters')],
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
            this.model.set('num_seats', parseInt(this.$el.find('.num_winners').val()));
            this.model.set('min', parseInt(this.$el.find('.min_num_choices').val()));
            this.model.set('max', parseInt(this.$el.find('.max_num_choices').val()));
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-election_form_question_tab_pane").html());
            this.model.questionView = this;

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
            json.edit_election = (!ajax_data) ? false : true;
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
                        self.$el.find(".max_num_choices").attr('readonly', 'readonly');
                    }
                }
            });

            this.resetAnswers();
            this.$el.find("form").nod(this.getMetrics(), {
                silentSubmit: true,
                broadcastError: true,
                submitBtnSelector: ".hidden-input"
            });
            this.$el.find("form").submit(function (e) { e.preventDefault(); });
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
            e.preventDefault();
            e.stopPropagation();
            if (e.keyCode == 13) { // <Enter>
                this.userAddAnswer();
            }
            return false;
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
                this.$el.find(".max_num_choices").removeAttr('readonly');
            } else {
                this.$el.find(".num_winners_opts input").val('1');
                this.$el.find(".num_winners_opts").hide();
                this.$el.find(".max_num_choices").val('1');
                this.$el.find(".max_num_choices").attr('readonly', 'readonly');
            }
            this.model.set('tally_type', id);
        },

        createQuestion: function(e) {
            if (!this.$el.find("form").nod().formIsErrorFree()) {
                return;
            }
            // create the question
            this.updateModel();
            var model = this.model.clone();
            model.set("question_num", app.currentView.model.get('questions').length + 1);
            app.currentView.model.get('questions').add(model);

            // reset the add question tab
            this.resetForm();
        },
    });

    Agora.ElectionCreateForm = Backbone.View.extend({
        el: "div.top-form",

        initData: {},

        __initialLoading: false,

        getMetrics: function() {
            var self = this;

            var checkIntervalDate = function() {
                if (self.$el.find("#schedule_voting:checked").length == 0) {
                    return true;
                }
                var val_end = self.$el.find("#end_voting_date").val();
                var end_date = moment(val_end, "MM/DD/YYYY HH:mm");

                var val_start = self.$el.find("#start_voting_date").val();
                var start_date = moment(val_start, "MM/DD/YYYY HH:mm");
                return end_date != null && start_date != null && end_date - start_date >= 3600*1000;
            };

            return [
                ['#pretty_name', 'presence', gettext('This field is required')],
                ['#pretty_name', 'min-length:4', gettext('Must have at least 4 characters')],
                ['#description', 'presence', gettext('This field is required')],
                ['#description',  'min-length:4', gettext('Must be at least 4 characters long')],

                ['#start_voting_date', checkIntervalDate, gettext('Invalid dates')],
                ['#end_voting_date', checkIntervalDate, gettext('Invalid dates')],
            ];
        },

        events: {
            'click #schedule_voting': 'toggleScheduleVoting',
            'click #show_add_question_tab_btn': 'showAddQuestionTab',
            'click #schedule_voting_label': 'checkSchedule',
            'click .remove_question_btn': 'removeQuestion',
            'click .create_election_btn': 'saveElection',
        },

        getInitModel: function() {
            // ElectionModel contains a default
            return new Agora.ElectionModel();
        },

        modelToJsonForTemplate: function() {
            var json = this.model.toJSON();
            json.edit_election = false;
            return json;
        },

        initialize: function() {
            var log_error = function( event, data ) {
                console.log( data.el );
                console.log( data.msg );
            }
            $( window ).on( 'nod_error_fired', log_error );

            this.template = _.template($("#template-election_form").html());
            this.templateNavtab = _.template($("#template-election_form_question_navtab").html());

            _.bindAll(this);
            this.model = this.getInitModel();

            // render initial template
            this.$el.html(this.template(this.modelToJsonForTemplate()));

            // add question tab-content
            this.addQuestionView = new Agora.QuestionEditView({
                model: new Agora.QuestionModel({'question_num': 0}),
                electionFormView: this
            });
            this.$el.find('.tab-content').append(this.addQuestionView.render().el);

            // load initial models and listen to new ones
            this.listenTo(this.model.get('questions'), 'add', this.addQuestion);
            // prevents tabs to be shown as they are being added
            this.__initialLoading = true;
            this.model.get('questions').each(this.addQuestion);
            this.__initialLoading = false;

            // set selected security policy
            var self = this;
            this.$el.find("#id_voting_policy option").each(function() {
                if ($(this).attr('value') == self.model.get('security_policy')) {
                    $(this).attr('selected', 'selected');
                }
            })

            // update button on model changes and initialize
            this.listenTo(this.model, 'change', this.updateButtonsShown);
            this.listenTo(this.model.get('questions'), 'add', this.updateButtonsShown);
            this.listenTo(this.model.get('questions'), 'remove', this.updateButtonsShown);
            this.updateButtonsShown();

            // do various setup calls
            this.$el.find("#create_election_form").nod(this.getMetrics(),
                {silentSubmit: true, submitBtnSelector: ".hidden-input"});
            this.$el.find("form").submit(function (e) { e.preventDefault(); });

            $('.datetimepicker').datetimepicker();
            if (this.model.get("from_date")) {
                this.$el.find("#schedule_voting").click();
                $('div.top-form #schedule_voting_controls').toggle();
            }
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

        checkSchedule: function(e) {
            if ($("#schedule_voting:checked").length == 0) {
                $(e.target).closest(".error").removeClass('error');
            }
        },

        addQuestion: function(questionModel) {
            var i = questionModel.get('question_num');
            var newTab = this.templateNavtab({question_num: i});
            this.$el.find('#add-question-navtab').before(newTab);

            var view = new Agora.QuestionEditView({
                model: questionModel, electionFormView: this
            });
            this.$el.find('.tab-content').append(view.render().el);

            // if we're not loading the initial tabs, show the added question
            if (!this.__initialLoading) {
                $("#question-navtab-" + i +" a").tab('show');
            }
        },

        toggleScheduleVoting: function(e) {
            $('div.top-form #schedule_voting_controls').toggle(e.target.checked);
        },

        updateModel: function() {
            var start_date = this.$el.find("#start_voting_date").val();
            var end_date = this.$el.find("#end_voting_date").val();
            if ($("#schedule_voting:checked").length == 0) {
                this.model.set('from_date', '');
                this.model.set('to_date', '');
            } else {
                this.model.set('from_date', new Date(start_date).toJSON());
                this.model.set('to_date', new Date(end_date).toJSON());
            }
            this.model.set('pretty_name', this.$el.find('#pretty_name').val());
            this.model.set('description', this.$el.find('#description').val());
            this.model.set('short_description',
                this.model.get('description').substr(0, 140));
            this.model.set('security_policy',
                this.$el.find('#id_security_policy').val());
        },

        sendingData: false,

        saveElection: function(e) {
            e.preventDefault();

            // if we are already sending do nothing
            if (this.sendingData) {
                return;
            }

            // check that main election tab is being shown
            if (!$("#main-election-tab").hasClass("active")) {
                $("#main-election-tab a").tab('show');
            }

            // check that form is error free
            if (!this.$el.find("#create_election_form").nod().formIsErrorFree()) {
                return;
            }

            this.updateModel();

            // look for a question whose data is invalid, if any
            var failingQuestion = this.model.get('questions').find(function (question) {
                question.questionView.updateModel();
                return !question.questionView.$el.find("form").nod().formIsErrorFree();
            });

            // if found, switch to that question and return
            if (failingQuestion) {
                var question_num =failingQuestion.get('question_num');
                var selector = "#question-navtab-" + question_num + " a";
                this.$el.find(selector).tab('show');
                return;
            }

            // okey, we're going to send this new election - but first disable
            // the send question button to avoid sending the same thing multiple
            // times
            $(".create_election_btn").addClass("disabled");
            this.sendingData = true;

            var json = this.model.toJSON();
            json.action = 'create_election';
            var agora_id = $("#agora_id").val();
            var self = this;
            var jqxhr = $.ajax("/api/v1/agora/" + agora_id + "/action/", {
                data: JSON.stringifyCompat(json),
                contentType : 'application/json',
                type: 'POST',
            })
            .done(function(e) { window.location.href = e.url; })
            .fail(function(e) {
                self.sendingData = false;
                $(".create_election_btn").removeClass("disabled");
                var response = $.parseJSON(e.responseText);
                if (response.errors) {
                    alert(response.errors.__all__);
                } else {
                    alert(gettext("Error creating the election"));
                }
            });

            return false;
        },

        updateButtonsShown: function() {
            if (this.model.get("questions").length == 0) {
                this.$el.find(".create_election_btn").hide();
                this.$el.find("#save_election_btn").hide();
                this.$el.find("#show_add_question_tab_btn").show();
            } else {
                this.$el.find(".create_election_btn").show();
                this.$el.find("#save_election_btn").show();
                this.$el.find("#show_add_question_tab_btn").hide();
            }
        },

        showAddQuestionTab: function() {
            this.$el.find('.nav-tabs a:last').tab('show');
        }
    });

    Agora.ElectionEditForm = Agora.ElectionCreateForm.extend({

        getInitModel: function() {
            // here we filter the values to those that can be modified
            var from_date = moment(ajax_data.voting_starts_at_date);
            var to_date = moment(ajax_data.voting_ends_at_date);
            if (from_date) {
                from_date = from_date.format("MM/DD/YYYY HH:mm");
            }
            if (to_date) {
                to_date = to_date.format("MM/DD/YYYY HH:mm");
            }
            var initData = {
                id: ajax_data.id,
                pretty_name: ajax_data.pretty_name,
                description: ajax_data.description,
                comments_policy: ajax_data.comments_policy,
                security_policy: ajax_data.security_policy,
                questions: ajax_data.questions,
                from_date: from_date,
                to_date: to_date,
            };
            return new Agora.ElectionModel(initData);
        },

        modelToJsonForTemplate: function() {
            var json = this.model.toJSON();
            json.edit_election = (!ajax_data) ? false : true;
            return json;
        },

        sendingData: false,

        saveElection: function(e) {
            e.preventDefault();
            // if we are already sending do nothing
            if (this.sendingData) {
                return;
            }

            if (!this.$el.find("#create_election_form").nod().formIsErrorFree()) {
                return;
            }

            this.updateModel();

            // look for a question whose data is invalid
            var failingQuestion = this.model.get('questions').find(function (question) {
                question.questionView.updateModel();
                return !question.questionView.$el.find("form").nod().formIsErrorFree();
            });

            // if found, switch to that question
            if (failingQuestion) {
                var question_num =failingQuestion.get('question_num');
                var selector = "#question-navtab-" + question_num + " a";
                this.$el.find(selector).tab('show');
                return;
            }

            // okey, we're going to send this new election - but first disable
            // the send question button to avoid sending the same thing multiple
            // times
            this.$el.find("#save_election_btn").addClass("disabled");
            this.sendingData = true;

            var json = this.model.toJSON();
            if (json.from_date) {
                json.from_date = new Date(json.from_date).toJSON();
            }
            if (json.to_date) {
                json.to_date = new Date(json.to_date).toJSON();
            }
            var election_id = this.model.get('id');
            var self = this;
            var jqxhr = $.ajax("/api/v1/election/" + election_id + "/", {
                data: JSON.stringifyCompat(json), 
                contentType : 'application/json',
                type: 'PUT',
            })
            .done(function(e) { window.location.href = e.url; })
            .fail(function() { alert("Error saving the election"); })
            .always(function() {
                self.sendingData = false;
                self.$el.find("#save_election_btn").removeClass("disabled");
            });

            return false;
        },
    });
}).call(this);

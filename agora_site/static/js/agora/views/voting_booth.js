(function() {
    Agora.VoteAnswerModel = Backbone.AssociatedModel.extend({
        defaults: {
            'a': 'ballot/answer',
            'url': '',
            'details': '',
            'value': ''
        }
    });

    Agora.VoteQuestionModel = Backbone.AssociatedModel.extend({
        relations: [
            {
                type: Backbone.Many,
                key: 'answers',
                relatedModel: Agora.VoteAnswerModel
            },
            {
                type: Backbone.Many,
                key: 'user_answers',
                relatedModel: Agora.VoteAnswerModel
            },
        ],
        defaults: {
            'a': 'ballot/question',
            'tally_type': 'ONE_CHOICE',
            'question_num': 0,
            'max': 1,
            'min': 0,
            'num_seats': 1,
            'question': '',
            'randomize_answer_order': true,
            'answers': [],
            'user_answers': []
        }
    });

    Agora.VoteElectionModel = Backbone.AssociatedModel.extend({
        relations: [{
            type: Backbone.Many,
            key: 'questions',
            relatedModel: Agora.VoteQuestionModel
        }],
        defaults: {
            'pretty_name': '',
            'description': '',
            'is_vote_secret': true,
            'user_vote_is_secret': true,
            'questions': [],
            'from_date': '',
            'to_date': ''
        },
        initialize: function() {
            var self = this;
            this.get('questions').each(function (element, index, list) {
                element.set('question_num', index);
                element.set('num_questions', list.length);
                element.set('election_name', self.get('pretty_name'));
            })
        },
    });

    Agora.VotingBooth = Backbone.View.extend({
        el: "#voting_booth",

        events: {
            'click .btn-start-voting': 'startVoting',
        },

        reviewMode: false,

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth").html());

            // ajax_data is a global variable
            this.model = new Agora.VoteElectionModel(ajax_data);
            this.render();

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));

            // create start view
            this.startScreenView = new Agora.VotingBoothStartScreen({model: this.model});
            this.$el.find(".current-screen").append(this.startScreenView.render().el);

            // create a view per question
            this.questionViews = [];
            var self = this;
            this.model.get('questions').each(function (element, index, list) {
                self.questionViews[index] = self.createQuestionView(element);
            });

            // create review questions view for later
            this.reviewQuestions = new Agora.ReviewQuestionsView({model: this.model, votingBooth: this});

            // create vote caste view for later
            this.voteCast = new Agora.VoteCastView({model: this.model, votingBooth: this});

            this.delegateEvents();

            return this;
        },

        /**
         * Creates a question view. The class used depends on the voting system
         * used in that question.
         */
        createQuestionView: function (model) {
            var voting_system = model.get('tally_type');
            if (voting_system == "ONE_CHOICE") {
                return new Agora.VotePluralityQuestion({model: model, votingBooth: this});
            } else if (voting_system == "MEEK-STV") {
                return new Agora.VoteRankedQuestion({model: model, votingBooth: this});
            }
        },

        /**
         * Shows the first question
         */
        startVoting: function() {
            this.$el.find(".current-screen").html('');
            this.$el.find(".current-screen").append(this.questionViews[0].render().el)
        },

        /**
         * Invokes the next step. The first argument is the number of the
         * question from which the user clicked continue
         */
        nextStep: function(question_num) {
            var size = this.model.get('questions').length;
            this.$el.find(".current-screen").html('');

            if (question_num + 1 == size || this.reviewMode) {
                this.reviewMode = true;
                this.$el.find(".current-screen").append(this.reviewQuestions.render().el);
                return;
            }

            this.$el.find(".current-screen").append(this.questionViews[question_num + 1].render().el);
        },

        changeQuestionChoices: function(question_num) {
            this.$el.find(".current-screen").html('');
            this.$el.find(".current-screen").append(this.questionViews[question_num].render().el);
        },

        sendingData: false,

        castVote: function() {
            if (this.sendingData) {
                return;
            }

            // do not set ballot twice
            this.sendingData = true;
            $("#cast-ballot-btn").addClass("disabled");

            var user_vote_is_secret = (this.$el.find("#user_vote_is_public:checked").length == 0);

            var ballot = {
                'is_vote_secret': user_vote_is_secret,
                'action': 'vote'
            };
            this.model.get('questions').each(function (element, index, list) {
                var user_answers = element.get('user_answers').pluck('value');
                var voting_system = element.get('tally_type');
                if (voting_system == "ONE_CHOICE") {
                    if (user_answers.length > 0) {
                        ballot['question' + index] = user_answers[0];
                    } else {
                        ballot['question' + index] = "";
                    }
                } else if (voting_system == "MEEK-STV") {
                    ballot['question' + index] = user_answers;
                }
            });
            var election_id = this.model.get('id');

            var self = this;
            var jqxhr = $.ajax("/api/v1/election/" + election_id + "/action/", {
                data: JSON.stringify(ballot),
                contentType : 'application/json',
                type: 'POST',
            })
            .done(function(e) {
                self.$el.find(".current-screen").html('');
                self.$el.find(".current-screen").append(self.voteCast.render().el);
            })
            .fail(function() {
                self.sendingData = false;
                self.$el.find("#cast-ballot-btn").removeClass("disabled");
                alert("Error casting the ballot, try again or report this problem");
            });

        }
    });

    Agora.VotingBoothStartScreen = Backbone.View.extend({
        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_start_screen").html());

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));
            var converter = new Showdown.converter();
            var self = this;
            this.$el.find('.markdown-readonly').each(function (index) {
                var data_id = $(this).data('id');
                $(this).html(converter.makeHtml(self.model.get(data_id)));
            });
            this.delegateEvents();
            return this;
        },
    });

    Agora.VotePluralityQuestion = Backbone.View.extend({
        events: {
            'click input': 'selectChoice',
            'click .remove-selection': 'removeSelection',
            'click .btn-continue': 'continueClicked',
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_question_plurality").html());
            this.votingBooth = this.options.votingBooth;

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));

            // shuffle options
            if (this.model.get('randomize_answer_order')) {
                this.$el.find('.plurality-options').shuffle();
            }

            // restore selected option from model if any
            if (this.model.get('user_answers').length > 0) {
                var self = this;
                var currentSelection = this.model.get('user_answers').at(0).get('value');
                this.$el.find('label input').each(function (index) {
                    if ($(this).val() == currentSelection) {
                        $(this).attr('checked', 'checked');
                        $(this).closest('label').addClass('active');
                    }
                });
            }
            this.delegateEvents();
            return this;
        },

        selectChoice: function(e) {
            // highlight
            this.$el.find('label.active').removeClass('active');
            $(e.target).closest('label').addClass('active');

            // hide error info box
            this.$el.find('.select-info').hide();

            // find user choice
            var value = $(e.target).val();
            var newSelection;
            this.model.get('answers').each(function (element, index, list) {
                if (element.get('value') == value) {
                    newSelection = element.clone();
                }
            });

            // remove previous choice
            if (this.model.get('user_answers').length > 0) {
                this.model.get('user_answers').at(0).destroy();
            }
            // set new choice
            this.model.get('user_answers').add(newSelection);
        },

        removeSelection: function() {
            // uncheck
            this.$el.find('label.active input').prop('checked', false);

            // make inactive
            this.$el.find('label.active').removeClass('active');

            // remove previous choice
            if (this.model.get('user_answers').length > 0) {
                this.model.get('user_answers').at(0).destroy();
            }
        },

        continueClicked: function() {
            if (this.model.get('min') == 0) {
                this.nextStep();
                return;
            }

            if (this.$el.find('label.active').length == 0) {
                this.$el.find('.select-info').show();
                return;
            }

            this.nextStep();
        },

        nextStep: function() {
            this.votingBooth.nextStep(this.model.get('question_num'));
        }
    });

    Agora.VoteRankedQuestion = Backbone.View.extend({
        events: {
            'click .available-choices li a': 'selectChoice',
            'click .btn-continue': 'continueClicked',
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_question_ranked").html());
            this.templateChoice = _.template($("#template-voting_booth_question_ranked_choice").html());
            this.votingBooth = this.options.votingBooth;

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));

            // shuffle options
            if (this.model.get('randomize_answer_order')) {
                this.$el.find('.available-choices ul').shuffle();
            }

            var self = this;
            var selection = [];
            // restore selected options from model if any
            this.model.get('user_answers').each(function (element, index, list) {
                var value = element.get('value');
                var target = null;
                self.$el.find('.available-choices ul li').each(function (index) {
                    if ($(this).data('value') == value) {
                        target = this;
                    }
                });

                // simulate user clicked it
                selection[index] = target;
            });

            this.model.get('user_answers').reset();
            _.each(selection, function (element, index, list) {
                self.selectChoice({target: element});
            });

            this.delegateEvents();
            return this;
        },

        /**
         * Continues to next question or review view if this is the last question
         */
        continueClicked: function() {
            var length = this.model.get('user_answers').length;
            if (length < this.model.get('min')) {
                this.$el.find('.need-select-more').show();
                return;
            }

            this.nextStep();
        },

        /**
         * Selects a choice from the available choices list, adding it to the
         * ballot and marking it as selected.
         */
        selectChoice: function(e) {
            var liEl = $(e.target).closest('li');
            var value = liEl.data('value');
            var length = this.model.get('user_answers').length;

            // find user choice
            var newSelection;
            this.model.get('answers').each(function (element, index, list) {
                if (element.get('value') == value) {
                    newSelection = element.clone();
                }
            });

            // select
            if (!liEl.hasClass('active')) {
                if (length >= this.model.get('max')) {
                    return;
                }
                // mark selected
                liEl.addClass('active');
                liEl.find('i').removeClass('icon-chevron-right');
                liEl.find('i').addClass('icon-chevron-left');
                liEl.find('i').addClass('icon-white');

                // add to user choices
                var templData = {
                    value: value,
                    i: length + 1
                };
                var newChoiceLink = this.templateChoice(templData);
                var newChoice = $(document.createElement('li'));
                newChoice.data('value', value);
                newChoice.html(newChoiceLink);
                this.$el.find('.user-choices ul').append(newChoice);

               // add choice to model
                this.model.get('user_answers').add(newSelection);

                // show/hide relevant info
                if (length + 1 == this.model.get('min')) {
                    this.$el.find('.need-select-more').hide();
                }
                if (length + 1 == this.model.get('max')) {
                    this.$el.find('.cannot-select-more').show();
                }
            }
            // deselect
            else {
                // unmark selected
                liEl.removeClass('active');
                liEl.find('i').addClass('icon-chevron-right');
                liEl.find('i').removeClass('icon-chevron-left');
                liEl.find('i').removeClass('icon-white');

                // find user choice
                var userChoice = null;
                this.$el.find('.user-choices ul li').each(function (index) {
                    if ($(this).data('value') == value) {
                        userChoice = $(this);
                    }
                    // renumerate
                    if (userChoice) {
                        $(this).find('small').html(index + ".");
                    }
                });

                // remove from user choices
                userChoice.remove()

                // remove choice from model
                this.model.get('user_answers').each(function (element, index, list) {
                    if (element.get('value') == value) {
                        element.destroy();
                    }
                });

                // show/hide relevant info
                if (length - 1 < this.model.get('max')) {
                    this.$el.find('.cannot-select-more').hide();
                }
            }
        },

        nextStep: function() {
            this.votingBooth.nextStep(this.model.get('question_num'));
        }
    });


    Agora.ReviewQuestionsView = Backbone.View.extend({
        events: {
            'click th a': 'changeQuestionChoices',
            'click #cast-ballot-btn': 'continueClicked',
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_review_questions").html());
            this.votingBooth = this.options.votingBooth;

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));
            this.delegateEvents();

            // user cannot vote secretly
            if (this.model.get('user_perms').indexOf('vote_counts') == -1) {
                this.$el.find("#user_vote_is_public").attr('checked', 'checked');
                this.$el.find("#user_vote_is_public").attr('disabled', true);
                this.$el.find("#user_vote_is_public").closest('label').find('span.optional').hide();
                this.$el.find("#user_vote_is_public").closest('label').find('span.mandatory').removeClass('hide');
            }
            return this;
        },

        changeQuestionChoices: function(e) {
            this.votingBooth.changeQuestionChoices($(e.target).data('id'));
        },

        continueClicked: function(e) {
            this.votingBooth.castVote();
        }
    });

    Agora.VoteCastView = Backbone.View.extend({
        events: {},

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_vote_cast").html());
            this.votingBooth = this.options.votingBooth;

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));
            this.delegateEvents();
            return this;
        }
    });
}).call(this);

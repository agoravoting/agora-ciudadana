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
                return new Agora.VotePluralityQuestion({model: model, votingBooth: this});
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

            this.$el.find(".current-screen").append(this.questionViews[question_num].render().el);
        },

        changeQuestionChoices: function(question_num) {
            this.$el.find(".current-screen").html('');
            this.$el.find(".current-screen").append(this.questionViews[question_num].render().el);
        },

        castVote: function() {
            this.$el.find(".current-screen").html('');
            this.$el.find(".current-screen").append(this.voteCast.render().el);
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
            if (this.model.get('randomize_answer_order')) {
                this.$el.find('.plurality-options').shuffle();
            }

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

    Agora.ReviewQuestionsView = Backbone.View.extend({
        events: {
            'click th a': 'changeQuestionChoices',
            'click .btn-continue': 'continueClicked',
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
            return this;
        },

        changeQuestionChoices: function(e) {
            this.votingBooth.changeQuestionChoices($(e.target).data('id'));
        },

        continueClicked: function() {
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

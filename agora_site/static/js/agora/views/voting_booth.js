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
            'user_answers': [],
            'next_is_review': false
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
                element.set('min', 1);
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

            return this;
        },

        /**
         * Creates a question view. The class used depends on the voting system
         * used in that question.
         */
        createQuestionView: function (model) {
            var voting_system = model.get('tally_type');
            if (voting_system != "ONE_CHOICE") {
                return new Agora.VotePluralityQuestion({model: model});
            } else if (voting_system == "MEEK-STV") {
                return new Agora.VotePluralityQuestion({model: model});
            }
        },

        /**
         * Shows the first question
         */
        startVoting: function() {
            this.$el.find(".current-screen").html('');
            this.$el.find(".current-screen").append(this.questionViews[0].render().el)
        },
    });

    Agora.VotingBoothStartScreen = Backbone.View.extend({
        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_start_screen").html());
            this.render();

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
            return this;
        },
    });

    Agora.VotePluralityQuestion = Backbone.View.extend({
        events: {
            'click input': 'selectChoice',
            'click .btn-continue': 'continueClicked',
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_question_plurality").html());
            this.render();

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));
            return this;
        },

        selectChoice: function(e) {
            this.$el.find('label').removeClass('active');
            $(e.target).closest('label').addClass('active');
            this.$el.find('.select-info').hide();
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
            // TODO
        }
    });
}).call(this);

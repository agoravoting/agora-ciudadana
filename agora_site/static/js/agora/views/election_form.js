(function() {
    Agora.ElectionModel = Backbone.Model.extend({});

    Agora.QuestionModel = Backbone.Model.extend({});

    Agora.QuestionEditView = Backbone.View.extend({
        tagName: 'div',

        className: 'tab-pane',

        id: function() {
            return "question-tab-" + this.model.get('question_num');
        },

        initialize: function() {
            this.template = _.template($("#template-election_form_question_tab_pane").html());
            this.$el.html(this.template(this.model.toJSON()));
        }
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
        },

        getInitModel: function() {
            return {
                'pretty_name': '',
                'description': '',
                'is_vote_secret': true,
                'questions': []
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
                model: new Agora.QuestionModel({question_num: 0})});
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

        checkStartDate: function() {
            if (!$("#schedule_voting:checked").length == 0) {
                return true;
            }
            var val = this.$el.find("#start_voting_date").val();
            if (!val) {
                return true;
            }
            return isFinite(new Date(val));
        },

        checkEndDate: function() {
            if (!$("#schedule_voting:checked").length == 0) {
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
//                 this.$el.find("#create_election_btn").hide();
//                 this.$el.find("#show_add_question_tab_btn").show();
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

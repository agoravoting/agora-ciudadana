(function() {
    Agora.VoteAnswerModel = Backbone.AssociatedModel.extend({
        defaults: {
            'a': 'ballot/answer',
            'url': '',
            'details': '',
            'value': ''
        }
    });

    Agora.checkWebWorkersAvailable = function() {
        return typeof(Worker) !== "undefined";
    }

    Agora.emailChecker = function(v) {
        var RFC822;
        RFC822 = /^([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22))*\x40([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d))*$/;
        return RFC822.test(v);
    }

    Agora.encryptAnswer = function(pk_json, plain_answer) {
        /**
         * Here we not only just encrypt the answer but also provide a
         * verifiable Proof of Knowledge (PoK) of the plaintext, using the
         * Schnorr Protocol with Fiat-Shamir (which is a method of
         * converting an interactive PoK into non interactive using a hash
         * that substitutes the random oracle). We use sha256 for hashing.
         */
        var pk = ElGamal.PublicKey.fromJSONObject(pk_json);
        var plaintext = new ElGamal.Plaintext(BigInt.fromInt(plain_answer), pk, true);
        var randomness = Random.getRandomInteger(pk.q);
        var ctext = ElGamal.encrypt(pk, plaintext, randomness);
        var proof = plaintext.proveKnowledge(ctext.alpha, randomness, ElGamal.fiatshamir_dlog_challenge_generator);
        var ciphertext =  ctext.toJSONObject();
        var proof = proof.toJSONObject();
        var enc_answer = {
            alpha: ciphertext.alpha,
            beta: ciphertext.beta,
            commitment: proof.commitment,
            response: proof.response,
            challenge: proof.challenge
        };

//         var verified = ctext.verifyPlaintextProof(proof, ElGamal.fiatshamir_dlog_challenge_generator);
//         console.log("is proof verified = " + new Boolean(verified).toString());
        return enc_answer;
    }

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
            'security_policy': 'PUBLIC_VOTING',
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
            'click #user_vote_is_public': 'toggleWhy'
        },

        reviewMode: false,

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth").html());
            this.templateEncrypting = _.template($("#template-voting_booth_encrypting").html());

            // ajax_data is a global variable
            ajax_data.has_to_authenticate = has_to_authenticate;
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

        toggleWhy: function(e) {
            var user_vote_is_secret = (this.$el.find("#user_vote_is_public:checked").length == 0);
            if (user_vote_is_secret) {
                $("#why_id").hide();
            } else {
                $("#why_id").show();
            }
        },

        castVote: function() {
            if (this.sendingData) {
                return;
            }

            // do not set ballot twice
            this.sendingData = true;
            var user_vote_is_encrypted = ajax_data.security_policy == "ALLOW_ENCRYPTED_VOTING";
            if (user_vote_is_encrypted) {
                this.$el.find(".current-screen").html('');
                this.$el.find(".current-screen").html(this.templateEncrypting(this.model.toJSON()));
            }

            var user_vote_is_secret = (this.$el.find("#user_vote_is_public:checked").length == 0);

            this.ballot = {
                'is_vote_secret': user_vote_is_secret,
                'action': 'vote'
            };

            if (!user_vote_is_secret) {
                var why = $("#why_id").val();
                this.ballot['reason'] = why;
            }
            var self = this;
            this.model.get('questions').each(function (element, index, list) {
                var user_answers = element.get('user_answers').pluck('value');
                var voting_system = element.get('tally_type');
                if (voting_system == "ONE_CHOICE") {
                    if (user_answers.length > 0) {
                        self.ballot['question' + index] = user_answers[0];
                    } else {
                        self.ballot['question' + index] = "";
                    }
                } else if (voting_system == "MEEK-STV") {
                    self.ballot['question' + index] = user_answers;
                }
            });

            if (user_vote_is_encrypted) {
                this.nextquestionToEncryptIndex = 0;
                $("html").attr("style", "height: 100%; cursor: wait !important;");
                setTimeout(this.encryptNextQuestion, 300);
            } else {
                this.eventVoteSealed();
            }
        },

        encryptNextQuestion: function() {
             if (this.nextquestionToEncryptIndex >= ajax_data.questions.length) {
                this.eventVoteSealed();
                return;
             }
            var index = this.nextquestionToEncryptIndex;
            this.nextquestionToEncryptIndex = index + 1;

            var possible_answers = _.pluck(ajax_data.questions[index].answers, "value");
            var choice_index = possible_answers.indexOf(this.ballot['question' + index]);
            if (choice_index == -1) {
                if (this.ballot['question' + index].length == 0) {
                    // blank vote is codified as possible_answers.length (which is invalid)
                    choice_index = possible_answers.length;
                } else {
                    // invalid vote is codified as possible_answers.length + 1 (which is invalid)
                    choice_index = possible_answers.length + 1;
                }

            }
            var percent_num = parseInt(((index+1)*100.0)/ajax_data.questions.length);

            this.ballot['issue_date'] = moment().format();
            this.ballot['question' + index] = Agora.encryptAnswer(
                ajax_data.pubkeys[index], choice_index);

            var percent = interpolate("width: %s%;",[percent_num]);
            $("#encrypt_progress").attr("style", percent);
            $("#encrypt_progress").html("" + percent_num + "%");
            setTimeout(this.encryptNextQuestion, 200);
        },


        eventVoteSealed: function() {
            $("html").attr("style", "");
            if (has_to_authenticate) {
                this.showAuthenticationForm();
                return;
            }
            this.sendBallot();
        },

        showAuthenticationForm: function() {
            if ($("#vote_fake").data("fakeit") == "yes-please") {
                this.$el.find(".current-screen").html('');
                this.$el.find(".current-screen").append(this.voteCast.render().el);
                return;
            }
            this.authenticateFormView = new Agora.AuthenticateFormView({model: this.model, votingBooth: this});
            this.$el.find(".current-screen").html('');
            this.$el.find(".current-screen").append(this.authenticateFormView.render().el);
        },

        sendBallot: function() {
            var election_id = this.model.get('id');

            if ($("#vote_fake").data("fakeit") == "yes-please") {
                this.$el.find(".current-screen").html('');
                this.$el.find(".current-screen").append(this.voteCast.render().el);
                return;
            }

            var self = this;
            var jqxhr = $.ajax("/api/v1/election/" + election_id + "/action/", {
                data: JSON.stringifyCompat(self.ballot),
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
        },

        showVoteSent: function(data) {
            this.voteCast.is_counted = data.is_counted;
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
            var data = this.model.toJSON();
            data.vote_isfake = $("#vote_fake").data("fakeit") == "yes-please";

            this.$el.html(this.template(data));
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
            var data = this.model.toJSON();
            this.$el.html(this.template(data));
            this.delegateEvents();

            // user cannot vote secretly
            var is_fake = $("#vote_fake").data("fakeit") == "yes-please";
            if (!is_fake && !has_to_authenticate &&
                    (this.model.get('user_perms').indexOf('vote_counts') == -1 ||
                    this.model.get('security_policy') == 'PUBLIC_VOTING')) {
                this.$el.find("#user_vote_is_public").attr('checked', 'checked');
                this.$el.find("#user_vote_is_public").attr('disabled', true);
                this.$el.find("#user_vote_is_public").hide();
                this.$el.find("#user_vote_is_public").closest('label').find('span.optional').hide();
                this.$el.find("#user_vote_is_public").closest('label').find('span.mandatory').removeClass('hide');
                this.$el.find(".mainlabel").hide();
            } else {
                this.$el.find("#why_id").hide();
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


    Agora.AuthenticateFormView = Backbone.View.extend({
        events: {
            'click a#loginAndVote': 'loginAndVote',
            'click a#fnmtLoginAndVote': 'fnmtLoginAndVote',
            'click a#registerAndVote': 'registerAndVote'
        },

        initialize: function() {
            _.bindAll(this);

            this.template = _.template($("#template-voting_booth_auth_screen").html());
            this.votingBooth = this.options.votingBooth;

            return this.$el;
        },

        sendingData: false,

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));
            this.delegateEvents();


            this.$el.find("#login_vote_form").nod(this.getLoginFormMetrics(), {
                silentSubmit: true,
                broadcastError: true,
                submitBtnSelector: ".hidden-input"
            });
            this.$el.find("#login_vote_form").submit(function (e) { e.preventDefault(); });

            this.$el.find("#register_vote_form").nod(this.getRegisterFormMetrics(), {
                silentSubmit: true,
                broadcastError: true,
                submitBtnSelector: ".hidden-input"
            });
            this.$el.find("#register_vote_form").submit(function (e) { e.preventDefault(); });

            return this;
        },

        getLoginFormMetrics: function() {
            var checkEmailOrName = function(val) {
                var username_rx = /^[a-zA-Z0-9-_]+$/;
                return Agora.emailChecker(val) || username_rx.test(val);
            }
            return [
                ['#id_identification', 'presence', gettext('This field is required')],
                ['#id_identification', 'min-length:3', gettext('Must have at least 3 characters')],
                ['#id_identification', checkEmailOrName, gettext('Invalid value')],
                ['#id_password', 'presence', gettext('This field is required')]
            ];
        },

        getRegisterFormMetrics: function() {
            var checkPass = function(val) {
                return val == $("#id_password1").val();
            };

            var checkScannedId = function(val) {
                return $("#id_scanned_id").get(0).files[0] != undefined;
            }
            return [
                ['#id_first_name', 'presence', gettext('This field is required')],
                ['#id_username', 'presence', gettext('This field is required')],
                ['#id_username', 'min-length:3', gettext('Must have at least 3 characters')],
                ['#id_email', 'presence', gettext('This field is required')],
                ['#id_email', 'email', gettext('Invalid email')],
                ['#id_password1', 'presence', gettext('This field is required')],
                ['#id_password2', 'presence', gettext('This field is required')],
                ['#id_password1', 'min-length:3', gettext('Must have at least 3 characters')],
                ['#id_password2', checkPass, gettext('Passwords do not match')],
                ['#id_scanned_id', checkScannedId, gettext('Attached a file')]
            ];
        },

        startSendingData: function() {
            this.sendingData = true;
            this.$el.find(".btn-large").addClass("disabled");
        },

        stopSendingData: function() {
            this.sendingData = false;
            this.$el.find(".btn-large").removeClass("disabled");
        },

        loginAndVote: function(e) {
            if (!this.$el.find("#login_vote_form").nod().formIsErrorFree()) {
                return;
            }

            var ballot = this.votingBooth.ballot;
            ballot['action'] = 'login_and_vote';
            ballot['user_id'] = this.$el.find("#id_identification").val();
            ballot['password'] = this.$el.find("#id_password").val();
            this.startSendingData();
            var self = this;
            var election_id = this.model.get('id');

            var jqxhr = $.ajax("/api/v1/election/" + election_id + "/action/", {
                data: JSON.stringifyCompat(ballot),
                contentType : 'application/json',
                type: 'POST',
            })
            .done(function(data) {
                self.stopSendingData();
                self.votingBooth.showVoteSent(data);
            })
            .fail(function(data) {
                self.stopSendingData();
                alert(gettext("Error casting the ballot. The given username probably doesn't exist. Try again or report this problem."));
            });
        },

        email_address: false,
        fnmtLoginAndVote: function(e) {
            var self = this;
            var url = AGORA_FNMT_BASE_URL + "/user/login/fnmt/";
            if (this.email_address) {
                url = url + "?email=" + this.email_address;
            }
            this.startSendingData();
            $.ajax({
                type: 'GET',
                url: url,
                dataType: 'jsonp',
                timeout : 1000000,
                success: function(json) {
                    if (json.needs_email) {
                        if (!self.email_address) {
                            var email = "";
                            var i = 0;
                            while (!Agora.emailChecker(email) && i < 2) {
                                email = window.prompt(gettext("Your FNMT certificate doesn't provide us an email address. Please, provide us your email address:"),"email@example.com");
                                if (!email) {
                                    alert(gettext("We are having trouble with your FNMT certificate. We recomend you to login from the web site front page and then try to vote again. Sorry for the inconvenience."))
                                    window.location.href="/";
                                }
                                i += 1;
                            }
                            self.email_address = email;
                            self.fnmtLoginAndVote();
                        } else {
                            alert(gettext("We are having trouble with your FNMT certificate. We recomend you to login from the web site front page and then try to vote again. Sorry for the inconvenience."))
                            window.location.href="/";
                        }
                    } else {
                        self.stopSendingData();
                        self.votingBooth.sendBallot();
                    }
                },
                error: function(e) {
                    self.stopSendingData();
                }
            });
        },

        registerAndVote: function(e) {
            if (!this.$el.find("#register_vote_form").nod().formIsErrorFree()) {
                return;
            }

            var ballot = this.votingBooth.ballot;
            ballot['action'] = 'register_and_vote';
            ballot['user_id'] = this.$el.find("#id_identification").val();
            ballot['password'] = this.$el.find("#id_password").val();
            this.startSendingData();
            var self = this;
            var election_id = this.model.get('id');
            ballot.election_id = election_id;
            $("#id_ballot_data").attr("value", JSON.stringifyCompat(ballot));

            var jqxhr = $.ajax("/accounts/signup_and_vote/", {
                type: 'POST',
                data: new FormData($('#register_vote_form')[0]),
                cache: false,
                contentType: false,
                processData: false
            })
            .done(function(data) {
                self.stopSendingData();
                self.votingBooth.showVoteSent(data);
            })
            .fail(function(data) {
                self.stopSendingData();
                alert(gettext("Error casting the ballot. The given username might already exist or the attached file is too big. Try again or report this problem."));
            });
        },
    });

    Agora.VoteCastView = Backbone.View.extend({
        events: {},

        is_counted: true,

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_vote_cast").html());
            this.votingBooth = this.options.votingBooth;

            return this.$el;
        },

        render: function() {
            // render template
            var data = this.model.toJSON();
            data.is_counted = this.is_counted;
            this.$el.html(this.template(data));
            this.delegateEvents();
            return this;
        }
    });
}).call(this);

(function() {
    Agora.VoteAnswerModel = Backbone.AssociatedModel.extend({
        defaults: {
            'a': 'ballot/answer',
            'urls': [],
            'details': '',
            'value': '',
            'media_url': '',
            'details_title': ''
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

    Agora.encryptAnswer = function(pk_json, encoded_answer, randomness) {
        /**
         * Here we not only just encrypt the answer but also provide a
         * verifiable Proof of Knowledge (PoK) of the plaintext, using the
         * Schnorr Protocol with Fiat-Shamir (which is a method of
         * converting an interactive PoK into non interactive using a hash
         * that substitutes the random oracle). We use sha256 for hashing.
         */
        var pk = ElGamal.PublicKey.fromJSONObject(pk_json);
        var plaintext = new
        ElGamal.Plaintext(encoded_answer, pk, true);
        if (!randomness) {
          randomness = Random.getRandomInteger(pk.q);
        } else {
          randomness = BigInt.fromJSONObject(randomness);
        }
        var ctext = ElGamal.encrypt(pk, plaintext, randomness);
        var proof = plaintext.proveKnowledge(ctext.alpha, randomness, ElGamal.fiatshamir_dlog_challenge_generator);
        var ciphertext =  ctext.toJSONObject();
        var json_proof = proof.toJSONObject();
        var enc_answer = {
            alpha: ciphertext.alpha,
            beta: ciphertext.beta,
            commitment: json_proof.commitment,
            response: json_proof.response,
            challenge: json_proof.challenge
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

        /**
         *  indicates that the vote is authenticated using a token given
         *  using the parameters ?message=whatever&sha1_hmac=whatever2
         */
        is_tokenized: false,

        jsonFromURL: function() {
            var query = decodeURI(document.location.search.substr(1));
            var data = query.split("&");
            var result = {};
            for (var i = 0; i < data.length; i++) {
                var item = data[i].split("=");
                result[item[0]] = decodeURIComponent(item[1]);
            }
            return result;
        },

        reviewMode: false,

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth").html());
            this.templateEncrypting = _.template($("#template-voting_booth_encrypting").html());

            // note, we have to do this before calling to render
            if (AGORA_USE_AUTH_TOKEN_VALIDATION  == "True") {
                var json_url = this.jsonFromURL();
                if (json_url.message && json_url.sha1_hmac) {
                    this.is_tokenized = true;
                    this.json_url = json_url;
                    ajax_data.is_tokenized = true;
                }
            }
            // ajax_data is a global variable
            ajax_data.has_to_authenticate = has_to_authenticate;
            this.model = new Agora.VoteElectionModel(ajax_data);
            this.render();

            return this.$el;
        },

        render: function() {
            // render template
            var data = this.model.toJSON();
            data.is_tokenized = this.is_tokenized;
            data.DEFAULT_FROM_EMAIL = DEFAULT_FROM_EMAIL;
            this.$el.html(this.template(data));

            // if agora is configured to use tokens and we didn't receive one,
            // this is a problem
            if(AGORA_USE_AUTH_TOKEN_VALIDATION == "True" && !this.is_tokenized) {
                document.location = AGORA_TOKEN_REDIRECT_IDENTIFY_URL;
            } else {
                // create start view
                this.startScreenView = new Agora.VotingBoothStartScreen({model: this.model});
                this.$el.find(".current-screen").append(this.startScreenView.render().el);
            }

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
            var layout = model.get('layout');
            if (voting_system == "ONE_CHOICE") {
                return new Agora.VotePluralityQuestion({model: model, votingBooth: this});
            } else if (voting_system == "MEEK-STV" || voting_system == "APPROVAL") {
                if (layout == "PRIMARY") {
                    return new Agora.VotePrimaryMultiQuestion({model: model, votingBooth: this, system: voting_system});
                } else { // simple
                    return new Agora.VoteMultiQuestion({model: model, votingBooth: this, system: voting_system});
                }
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
                } else if (voting_system == "MEEK-STV" || voting_system == "APPROVAL") {
                    self.ballot['question' + index] = user_answers;
                }
            });

            if (user_vote_is_encrypted) {
                this.nextquestionToEncryptIndex = 0;
                $("html").attr("style", "height: 100%; cursor: wait !important;");
                setTimeout(this.encryptNextQuestion, 300);
            } else {
                // we need to add some randomness to make vote unique so that
                // the hash is not repeated
                var random = sjcl.random.randomWords(5, 0);
                var rand_bi = new BigInt(sjcl.codec.hex.fromBits(random), 16);
                this.ballot['unique_randomness'] = rand_bi.toRadix(16);
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

            var data = this.questionViews[index].encodeQuestionAnswer(
                this.ballot['question' + index]);
            var decoded_data = this.questionViews[index].decodeQuestionAnswer(
                data);
            var decoded_data_str = JSON.stringifyCompat(decoded_data);
            var ballot_str = JSON.stringifyCompat(this.ballot['question' + index]);
            if (ballot_str != decoded_data_str) {
                alert(gettext("Sorry, but the codification of the vote failed. This is most likely a problem with your web browser. Please contact us telling information about what web browser and platform are you using to vote. We will redirect you now to the contact form."));
                window.location.href="/contact";
                return;
            }
            var percent_num = parseInt(((index+1)*100.0)/ajax_data.questions.length, 10);

            this.ballot['issue_date'] = moment().format();
            this.ballot['question' + index] = Agora.encryptAnswer(
                ajax_data.pubkeys[index], data);

            var percent = interpolate("width: %s%;",[percent_num]);
            $("#encrypt_progress").attr("style", percent);
            $("#encrypt_progress").html("" + percent_num + "%");
            setTimeout(this.encryptNextQuestion, 200);
        },


        eventVoteSealed: function() {
            $("html").attr("style", "");
            if (!this.is_tokenized && has_to_authenticate) {
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

            // tokenize the vote if needed
            if (this.is_tokenized) {
                this.ballot['action'] = 'token_vote';
                this.ballot['message'] = this.json_url.message;
                this.ballot['sha1_hmac'] = this.json_url.sha1_hmac;
            }

            var self = this;
            var jqxhr = $.ajax("/api/v1/election/" + election_id + "/action/", {
                data: JSON.stringifyCompat(self.ballot),
                contentType : 'application/json',
                type: 'POST',
            })
            .done(function(e) {
                ajax_data.ballot = self.ballot;
                self.$el.find(".current-screen").html('');
                self.$el.find(".current-screen").append(self.voteCast.render().el);
            })
            .fail(function(jqXHR, textStatus) {
                self.sendingData = false;
                self.$el.find("#cast-ballot-btn").removeClass("disabled");
                if (jqXHR.text.indexOf("token") != -1) {
                    alert(gettext("There was a problem casting the ballot. You might have already voted, or your identification might have expired. We recommend you to try to identify yourself again."));
                    document.location.href = AGORA_TOKEN_REDIRECT_IDENTIFY_URL;
                } else {
                    alert(gettext("Error casting the ballot, try again or report this problem"));
                }
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
            data.is_tokenized = ajax_data.is_tokenized;

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

            // do some sanity checks
            this.sanityChecks();

            return this.$el;
        },

        /**
         * Do some vote encoding tests
         */
        sanityChecks: function () {
            var user_vote_is_encrypted = ajax_data.security_policy == "ALLOW_ENCRYPTED_VOTING";
            if (!user_vote_is_encrypted) {
                return;
            }
            try {
                var question = this.model.toJSON();
                var possible_answers = _.pluck(question.answers, "value");

                // test 10 random ballots. Note, we won't honor the limits of number
                // of options for this question for simplicity, we'll just do some
                // tests to assure everything is fine.
                for (var i = 0; i < 10; i++) {
                    // generate ballot
                    var rnd = Math.ceil(Math.random() * 10000) % possible_answers.length;
                    var opt = possible_answers[rnd];
                    var ballot = opt;
                    // check encode -> decode pipe doesn't modify the ballot
                    var encoded = this.encodeQuestionAnswer(ballot);
                    var decoded = JSON.stringifyCompat(this.decodeQuestionAnswer(encoded));
                    if (ballot != decoded) {
                        throw "error";
                    }
                }

                // test blank vote
                var encoded = this.encodeQuestionAnswer("");
                var decoded = JSON.stringifyCompat(this.decodeQuestionAnswer(encoded));
                if (JSON.stringifyCompat([]) != decoded) {
                    throw "error";
                }
            } catch (e) {
                alert(gettext("Sorry, but we have detected errors when doing some sanity automatic checks which prevents to assure that you can vote with this web browser. This is most likely a problem with your web browser. Please contact us telling information about what web browser and platform are you using to vote. We will redirect you now to the contact form."));
                window.location.href = "/contact";
            }
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

        /**
         *  Encode an answer into a bigint. Example: "A" --> 1 -> BigInt(1)
         */
        encodeQuestionAnswer: function(data) {
            /**
             * Gets the answer in an encoded, encryptable way as a BigInt
             */
            var question = this.model.toJSON();
            var possible_answers = _.pluck(question.answers, "value");
            var choice_index = _.indexOf(possible_answers, data);
            if (choice_index == -1) {
                // invalid vote is codified as possible_answers.length + 1 (which is invalid)
                choice_index = possible_answers.length + 1;

            }
            return BigInt.fromInt(choice_index);
        },

        /**
         * Does exactly the reverse of of encodeQuestionAnswer. It should be
         * such as the following statement is always true:
         *
         * data == decodeQuestionAnswer(encodeQuestionAnswer(data))
         *
         * This function is very useful for sanity checks.
         */
        decodeQuestionAnswer: function(encoded_data) {
            var question = this.model.toJSON();
            var possible_answers = _.pluck(question.answers, "value");
            var encoded_str = encoded_data.toJSONObject();
            var encoded_index = parseInt(encoded_str, 10);

            // this is a blank vote
            if (encoded_index == possible_answers.length + 1) {
                return "";
            }
            return possible_answers[encoded_index];
        },

        nextStep: function() {
            this.votingBooth.nextStep(this.model.get('question_num'));
        }
    });

    Agora.VoteMultiQuestion = Backbone.View.extend({
        events: {
            'click .available-choices li a': 'selectChoice',
            'click .btn-continue': 'continueClicked',
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_question_ranked").html());
            this.system = this.options.system;
            if(this.system == "APPROVAL") {
                this.templateChoice = _.template($("#template-voting_booth_question_approval_choice").html());
            }
            else {
                this.templateChoice = _.template($("#template-voting_booth_question_ranked_choice").html());
            }

            this.votingBooth = this.options.votingBooth;


            // do some sanity checks
            this.sanityChecks();

            return this.$el;
        },

        /**
         * Do some vote encoding tests
         */
        sanityChecks: function () {
            var user_vote_is_encrypted = ajax_data.security_policy == "ALLOW_ENCRYPTED_VOTING";
            if (!user_vote_is_encrypted) {
                return;
            }
            try {
                var question = this.model.toJSON();
                var possible_answers = _.pluck(question.answers, "value");

                // test 10 random ballots. Note, we won't honor the limits of number
                // of options for this question for simplicity, we'll just do some
                // tests to assure everything is fine.
                for (var i = 0; i < 10; i++) {
                    // generate ballot
                    var ballot = [];
                    var n_selected_options = Math.ceil(Math.random() * 10000) % possible_answers.length;
                    for (var j = 0; j < n_selected_options; j++) {
                        var rnd = Math.ceil(Math.random() * 10000) % possible_answers.length;
                        var opt = possible_answers[rnd];
                        // do not duplicate options
                        if (_.indexOf(ballot, opt) == -1) {
                            ballot.push(opt);
                        }
                    }
                    // check encode -> decode pipe doesn't modify the ballot
                    var encoded = this.encodeQuestionAnswer(ballot);
                    var decoded = JSON.stringifyCompat(this.decodeQuestionAnswer(encoded));
                    if (JSON.stringifyCompat(ballot) != decoded) {
                        throw "error";
                    }
                }

                // test blank vote
                var encoded = this.encodeQuestionAnswer([]);
                var decoded = JSON.stringifyCompat(this.decodeQuestionAnswer(encoded));
                if (JSON.stringifyCompat([]) != decoded) {
                    throw "error";
                }
            } catch (e) {
                alert(gettext("Sorry, but we have detected errors when doing some sanity automatic checks which prevents to assure that you can vote with this web browser. This is most likely a problem with your web browser. Please contact us telling information about what web browser and platform are you using to vote. We will redirect you now to the contact form."));
                window.location.href = "/contact";
            }
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

        /**
         * Converts a vote into a BigInt. A vote in this case is a list of
         * preferences, for example ['A', 'C'], which is translated this way:
         *
         * A --> first option, so we convert it to the number 1
         * C --> third option, so we convert it to the number 3
         *
         * Options are converted to numbers starting from 1. We don't use zero
         * because it would cause encoding problems. Next step is converting
         * those number to strings of fixed size:
         *
         * ['A', 'C']  --> [1, 3] -> ['01', '03']
         *
         * We need to be sure that each option will always be encoded using the
         * the same number of characters so that decoding the options is
         * possible in a deterministic way. So if we have 24 options, we know
         * that we can codify any of those options with 2 characters, but if we
         * have 110 options we need three chars per option.
         *
         * Next step is to concatenate the ordered list of option strings:
         *
         * ['A', 'C']  --> [1, 3] -> ['01', '03'] -> '0103'
         *
         * After that, we have a number to be encrypted. We convert this number
         * to integer and then to a BigInt, and return it:
         *
         * ['A', 'C']  --> [1, 3] -> ['01', '03'] -> '0103' -> 103 -> BigInt(103)
         *
         * NOTE: the zeros at the left of the final number are removed, because
         * a number representation never has any zeros at the left. When
         * doing decoding of the result you should take this into account.
         */
        encodeQuestionAnswer: function(data) {
            var question = this.model.toJSON();
            var possible_answers = _.pluck(question.answers, "value");
            var ret_data = "";
            var numChars = (possible_answers.length + 2).toString(10).length;
            _.each(data, function (element, i, list) {
                var choice_index = _.indexOf(possible_answers, element);
                ret_data = ret_data + Agora.numberToString(choice_index + 1, numChars);
            });
            // blank vote --> make it not count using possible_answers.length + 2;
            if (ret_data.length == 0) {
                ret_data = Agora.numberToString(possible_answers.length + 2, numChars);
            }
            var ret_val = new BigInt(ret_data, 10);

            return ret_val;
        },

        /**
         * Does exactly the reverse of of encodeQuestionAnswer. It should be
         * such as the following statement is always true:
         *
         * data == decodeQuestionAnswer(encodeQuestionAnswer(data))
         *
         * This function is very useful for sanity checks.
         */
        decodeQuestionAnswer: function(encoded_data) {
            var question = this.model.toJSON();
            var possible_answers = _.pluck(question.answers, "value");
            var encoded_str = encoded_data.toJSONObject();
            var tab_nchars = (possible_answers.length + 2).toString(10).length;

            // check if it's a blank vote
            if (parseInt(encoded_str, 10) == possible_answers.length + 2) {
                return [];
            }

            // add zeros to the left for tabulation
            var length = encoded_str.length;
            for (var i = 0; i < (length % tab_nchars); i++) {
                encoded_str = "0" + encoded_str;
            }

            // decode each option
            var ret_val = []
            for (var i = 0; i < (encoded_str.length / tab_nchars); i++) {
                var option_str = encoded_str.substr(i*tab_nchars, tab_nchars);
                var option_index = parseInt(option_str, 10);
                var opt_str = possible_answers[option_index - 1];
                ret_val.push(opt_str);
            }
            return ret_val;
        },

        nextStep: function() {
            this.votingBooth.nextStep(this.model.get('question_num'));
        }
    });

    Agora.VotePrimaryMultiQuestion = Agora.VoteMultiQuestion.extend({
        events: {
            'click .available-choices li a.choose-option': 'selectChoice',
            'click .user-choices ul li a': 'deselectUserChoice',
            'click .btn-continue': 'continueClicked',
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_question_ranked_primary").html());
            this.system = this.options.system;
            if(this.system == "APPROVAL") {
                this.templateChoice = _.template($("#template-voting_booth_question_approval_choice").html());
            }
            else {
                this.templateChoice = _.template($("#template-voting_booth_question_ranked_choice").html());
            }
            this.votingBooth = this.options.votingBooth;
            app.modalDialog = new Agora.ModalDialogView();

            this.sanityChecks();

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
            setTimeout(self.addFiltering, 500);

            return this;
        },

        addFiltering: function() {
            var self = this;
            $('#filter-options').keyup(function() {
                clearTimeout($.data(this, 'timer'));
                var wait = setTimeout(self.filterOptions, 500);
                $(this).data('timer', wait);
            });

            // show details pop up
            $('a.option-link').click(function(e) {
                e.preventDefault();
                var liEl = $(e.target).closest('li');
                var value = liEl.data('value');

                // find user choice
                var answer;
                self.model.get('answers').each(function (element, index, list) {
                    if (element.get('value') == value) {
                        answer = element.toJSON();
                    }
                });

                var title = answer.value;
                var bodyTmpl = _.template($("#template-show_option_details_body").html());
                var body = bodyTmpl(answer);
                var footer = '<button type="button" class="btn btn-warning" data-dismiss="modal" aria-hidden="true">' + gettext("Close") + '</button>';

                app.modalDialog.populate(title, body, footer);
                app.modalDialog.show();

            });
        },

        filterOptions: function() {
            var val = $('#filter-options').val().toLowerCase();
            this.$el.find("ul.primary-options > li").each(function (index) {
                var value = $(this).data("value").toLowerCase();
                if (value.indexOf(val) != -1) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
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
            if (e && e.preventDefault) {
                e.preventDefault();
            }
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
                    $('html').scrollTop($(document).height());
                    return;
                }
                // mark selected
                liEl.addClass('active');

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

        /*
         * deselects an user choice
         */
        deselectUserChoice: function(e) {
            e.preventDefault();
            var liEl = $(e.target).closest('li');
            var value = liEl.data('value');
            var length = this.model.get('user_answers').length;

            // find user choice in the model
            var model;
            this.model.get('answers').each(function (element, index, list) {
                if (element.get('value') == value) {
                    model = element.clone();
                }
            });

            // find the item in the list of available choices and unmark as
            // selected
            this.$el.find('.available-choices ul li').each(function (index) {
                var availableChoice;
                if ($(this).data('value') == value) {
                    availableChoice = $(this);
                    // unmark selected
                    availableChoice.removeClass('active');
                }
            });

            // remove from user choices
            liEl.remove();

            // remove choice from model
            this.model.get('user_answers').each(function (element, index, list) {
                if (element.get('value') == value) {
                    element.destroy();
                }
            });

            // renumerate user choices
            this.$el.find('.user-choices ul li').each(function (index) {
                $(this).find('small').html((index + 1) + ".");
            });

            // show/hide relevant info
            if (length - 1 < this.model.get('max')) {
                this.$el.find('.cannot-select-more').hide();
            }
        },

        nextStep: function() {
            this.votingBooth.nextStep(this.model.get('question_num'));
        }
    });

    /**
     * Converts a number to a string. For example if number=23 and numCharts=3,
     * result="023"
     */
    Agora.numberToString = function(number, numChars) {
        var num_str = number.toString(10);
        var ret = num_str;
        for(var i = 0; i < numChars - num_str.length; i++) {
            ret = "0" + ret;
        }
        return ret;
    };

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

            if (ajax_data.agora.delegation_policy == "DISALLOW_DELEGATION" &&
                this.model.get('security_policy') != 'PUBLIC_VOTING')
            {
                this.$el.find("#user_vote_is_public").parent().hide();
                this.$el.find("#why_id").hide();
            }
             else if (!is_fake && !has_to_authenticate &&
                    (this.model.get('user_perms').indexOf('vote_counts') == -1 ||
                    this.model.get('security_policy') == 'PUBLIC_VOTING'))
            {
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
            ballot['issue_date'] = moment().format();
            ballot['user_id'] = this.$el.find("#id_identification").val();
            ballot['password'] = this.$el.find("#id_password").val();

            if (user_vote_is_encrypted) {
                // we need to add some randomness to make vote unique so that
                // the hash is not repeated
                var random = sjcl.random.randomWords(5, 0);
                var rand_bi = new BigInt(sjcl.codec.hex.fromBits(random), 16);
                ballot['unique_randomness'] = rand_bi.toRadix(16);
            }
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
                ajax_data.ballot = ballot;
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
            ballot['issue_date'] = moment().format();
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
                ajax_data.ballot = ballot;
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

            data.ballot_hash = Agora.hashBallot(ajax_data.ballot);
            ajax_data.ballot_hash =  data.ballot_hash;
            data.is_counted = this.is_counted;
            data.return_to_election = (AGORA_FRONT_PAGE != ajax_data.agora.full_name);
            data.is_tokenized = (AGORA_USE_AUTH_TOKEN_VALIDATION == "True");
            data.share_url = AGORA_TOKEN_REDIRECT_IDENTIFY_URL;
            if (!data.return_to_election) {
                data.url = "/";
            }
            this.$el.html(this.template(data));
            this.delegateEvents();
            return this;
        }
    });

    /**
     * Replacement for JSON.stringify in cases where the output needs to be
     * reproducable. In those cases, we have to sort the dictionaries before
     * stringifying them, something that JSON.stringify doesn't do.
     */
    Agora.jsonStringifySorted = function(obj) {
        if (Array.isArray(obj)) {
            var serialized = [];
            for(var i = 0; i < obj.length; i++) {
                serialized.push(Agora.jsonStringifySorted(obj[i]));
            }
            return "[" + serialized.join(", ") + "]";
        } else if (typeof(obj) == 'object') {
            if (obj == null) {
                return "null";
            }
            var sortedKeys = Object.keys(obj).sort();
            var arr = [];
            for(var i = 0; i < sortedKeys.length; i++) {
                var key = sortedKeys[i];
                var value = obj[key];
                key = JSON.stringify(key);
                value = Agora.jsonStringifySorted(value);
                arr.push(key + ': ' + value);
            }
            return "{" + arr.join(", ") + "}";
        } else {
            return JSON.stringify(obj);
        }
    };

    /**
     * Converts the ballot into the string that is used for hashing, and is
     * actually the format in which the vote is stored in the database and
     * how it will get stored in the tally.tar.gz
     */
    Agora.hashBallot = function(ballot) {
        var transformedBallot = {
            "a": "encrypted-vote-v1",
            "proofs": [],
            "choices": [],
            "issue_date": ballot.issue_date,
            "election_hash": {"a": "hash/sha256/value", "value": ajax_data.hash},
            "election_uuid": ajax_data.uuid
        }
        for (var i = 0; i < ajax_data.questions.length; i++) {
            var q_answer = ballot['question' + i];
            transformedBallot.proofs.push({
                "commitment":q_answer['commitment'],
                "response":q_answer['response'],
                "challenge":q_answer['challenge']
            });
            transformedBallot.choices.push({
                "alpha":q_answer['alpha'],
                "beta":q_answer['beta']
            });
        }
        var str_data = Agora.jsonStringifySorted(transformedBallot);
        var bitArray = sjcl.hash.sha256.hash(str_data);
        return sjcl.codec.hex.fromBits(bitArray);
    };
}).call(this);

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
            this.bw_template = _.template($("#template_background-wrapper-featured-election").html());
            this.question_template = _.template($("#template_featured-election-question").html());
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
                    if (data.q.a == "question/result/ONE_CHOICE") {
                        $("#bloques").append(this.oc_question_template(data));
                    } else {
                        $("#bloques").append(this.stv_question_template(data));
                    }
                }
            } else {
                for (var i = 0; i < ajax_data.election.questions.length; i++) {
                    var data = {
                        i: i,
                        q: ajax_data.election.questions[i]
                    };
                    $("#bloques").append(this.question_template(data));
                }
            }

            // in case there's only on question, uncollapse it
            if (ajax_data.election.questions.length == 1) {
                $("#q0").addClass("in");
            }

            var pk_json = {"g":"27257469383433468307851821232336029008797963446516266868278476598991619799718416119050669032044861635977216445034054414149795443466616532657735624478207460577590891079795564114912418442396707864995938563067755479563850474870766067031326511471051504594777928264027177308453446787478587442663554203039337902473879502917292403539820877956251471612701203572143972352943753791062696757791667318486190154610777475721752749567975013100844032853600120195534259802017090281900264646220781224136443700521419393245058421718455034330177739612895494553069450438317893406027741045575821283411891535713793639123109933196544017309147","p":"49585549017473769285737299189965659293354088286913371933804180900778253856217662802521113040825270214021114944067918826365443480688403488878664971371922806487664111406970012663245195033428706668950006712214428830267861043863002671272535727084730103068500694744742135062909134544770371782327891513041774499809308517270708450370367766144873413397605830861330660620343634294061022593630276805276836395304145517051831281606133359766619313659042006635890778628844508225693978825158392000638704210656475473454575867531351247745913531003971176340768343624926105786111680264179067961026247115541456982560249992525766217307447","q":"24792774508736884642868649594982829646677044143456685966902090450389126928108831401260556520412635107010557472033959413182721740344201744439332485685961403243832055703485006331622597516714353334475003356107214415133930521931501335636267863542365051534250347372371067531454567272385185891163945756520887249904654258635354225185183883072436706698802915430665330310171817147030511296815138402638418197652072758525915640803066679883309656829521003317945389314422254112846989412579196000319352105328237736727287933765675623872956765501985588170384171812463052893055840132089533980513123557770728491280124996262883108653723","y":"5383828687359633175167457781427171576794341933360862666155699443683378093084067322903153909147869270211909454109000037475463711858090937817089961996669436360851680043753399404247503586121519408689243902503807397936894430865478995603463706199441782503092456174491724912183336291543925768465738374804119979063155224354863963479242893806899154444635140493973491312715232651159541959188269501075455784792308595852813494423957501209842189151915522785324453109666734268519076890243666667963167602354494027277713699715567395330819944696895738803312321891165392405018562486913974801163499309171266032895339543830269614771098"};
            var answer = "23";

//             $("#congreso").html(this.encryptAnswer(answer, pk_json));
        },

        encryptAnswer: function(plain_answer, pk_json) {
            /**
             * Here we not only just encrypt the answer but also provide a
             * verifiable Proof of Knowledge (PoK) of the plaintext, using the
             * Schnorr Protocol with Fiat-Shamir (which is a method of
             * converting an interactive PoK into non interactive using a hash
             * that substitutes the random oracle). We use sha256 for hashing.
             */
            var pk = ElGamal.PublicKey.fromJSONObject(pk_json);
            var plaintext = new ElGamal.Plaintext(BigInt.fromJSONObject(plain_answer), pk, true);
            var randomness = Random.getRandomInteger(pk.q);
            var ctext = ElGamal.encrypt(pk, plaintext, randomness);
            var proof = plaintext.proveKnowledge(ctext.alpha, randomness, ElGamal.fiatshamir_dlog_challenge_generator);
            var enc_answer = {
                ciphertext: ctext.toJSONObject(),
                proof: proof.toJSONObject()
            };

            var verified = ctext.verifyPlaintextProof(proof, ElGamal.fiatshamir_dlog_challenge_generator);
            console.log("is proof verified = " + new Boolean(verified).toString());
            return JSON.stringifyCompat(enc_answer);
        }
    });
}).call(this)

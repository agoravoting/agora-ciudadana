(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.AgoraSettingsFormView = Backbone.View.extend({
        el: "#agora-settings-form",

        sendingData: false,

        events: {
            'click .available-choices li a': 'selectChoice',
            'click #save_profile': 'updateProfile',
            'click #save_configuration': 'updateConfiguration'
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-agora-settings-form").html());
            this.templateAuthority = _.template($("#template-authority-item").html());
            this.render();
        },

        render: function() {
            this.$el.html(this.template(ajax_data));

            // restore configuration
            this.$el.find('#id_delegation_policy option').each(function (element, index, list) {
                if ($(this).attr('value') == ajax_data.agora.delegation_policy) {
                    $(this).attr('selected', 'selected');
                }
            });
            if (ajax_data.agora.is_vote_secret == true) {
                this.$el.find("#id_is_vote_secret").attr("checked", "checked");
            }
            this.$el.find('#id_comments_policy option').each(function (element, index, list) {
                if ($(this).attr('value') == ajax_data.agora.comments_policy) {
                    $(this).attr('selected', 'selected');
                }
            });
            this.$el.find('#id_membership_policy option').each(function (element, index, list) {
                if ($(this).attr('value') == ajax_data.agora.membership_policy) {
                    $(this).attr('selected', 'selected');
                }
            });

            // shuffle options
            this.$el.find('.available-choices ul').shuffle();

            var self = this;
            var selection = [];
            // restore selected authorities if any
            _.each(ajax_data.agora_authorities, function (element, index, list) {
                var target = null;
                self.$el.find('.available-choices ul li').each(function (index) {
                    if ($(this).data('id') == element.id) {
                        target = this;
                    }
                });

                // simulate user clicked it
                selection[index] = target;
            });

            _.each(selection, function (element, index, list) {
                self.selectChoice({target: element});
            });

            this.delegateEvents();
            return this;
        },

        updateData: function(what) {
            if (this.sendingData) {
                return;
            }

            var data = null;
            if (what == 'profile') {
                data = {
                    pretty_name: this.$el.find("#id_pretty_name").val(),
                    short_description: this.$el.find("#id_short_description").val(),
                    biography: this.$el.find("#id_biography").val(),
                    is_vote_secret: ajax_data.agora.is_vote_secret,
                    membership_policy: ajax_data.agora.membership_policy,
                    comments_policy: ajax_data.agora.comments_policy,
                    delegation_policy: ajax_data.agora.delegation_policy
                };
            } else {
                data = {
                    pretty_name: ajax_data.agora.pretty_name,
                    short_description: ajax_data.agora.short_description,
                    biography: ajax_data.agora.biography,
                    is_vote_secret: this.$el.find("#id_is_vote_secret:checked").length == 1,
                    membership_policy: this.$el.find("#id_membership_policy").val(),
                    comments_policy: this.$el.find("#id_comments_policy").val(),
                    delegation_policy: this.$el.find("#id_delegation_policy").val()
                };
            }

            this.sendingData = true;
            this.$el.find("button[type=submit]").addClass("disabled");

            var self = this;
            var jqxhr = $.ajax("/api/v1/agora/" + ajax_data.agora.id + "/", {
                data: JSON.stringifyCompat(data),
                contentType : 'application/json',
                type: 'PUT',
            })
            .done(function(e) {
                window.location.reload();
            })
            .fail(function() {
                self.sendingData = false;
                self.$el.find("button[type=submit]").removeClass("disabled");
                alert(gettext("Sorry, error saving agora settings"));
            });
        },

        updateProfile: function(e) {
            e.preventDefault();
            this.updateData("profile");
        },

        updateConfiguration: function(e) {
            e.preventDefault();
            this.updateData("configuration");
        },

        /**
         * Selects a choice from the available choices list, adding it to the
         * list and marking it as selected.
         */
        selectChoice: function(e) {
            var liEl = $(e.target).closest('li');
            var id = liEl.data('id');
            var length = this.$el.find('.user-choices ul li').length;

            // find user choice
            var newSelection;
            _.each(ajax_data.available_authorities, function (element, index, list) {
                if (element.id == id) {
                    newSelection = element;
                }
            });

            // select
            if (!liEl.hasClass('active')) {
                if (length >= ajax_data.max_authorities) {
                    return;
                }
                // mark selected
                liEl.addClass('active');
                liEl.find('i').removeClass('icon-chevron-right');
                liEl.find('i').addClass('icon-chevron-left');
                liEl.find('i').addClass('icon-white');

                // add to user choices
                var templData = {
                    name: newSelection.name,
                    i: length + 1
                };
                var newChoiceLink = this.templateAuthority(templData);
                var newChoice = $(document.createElement('li'));
                newChoice.data('id', id);
                newChoice.html(newChoiceLink);
                this.$el.find('.user-choices ul').append(newChoice);

                // show/hide relevant info
                if (length + 1 == ajax_data.min_authorities) {
                    this.$el.find('.need-select-more').hide();
                }
                if (length + 1 == ajax_data.max_authorities) {
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
                    if ($(this).data('id') == id) {
                        userChoice = $(this);
                    }
                    // renumerate
                    if (userChoice) {
                        $(this).find('small').html(index + ".");
                    }
                });

                // remove from user choices
                userChoice.remove()

                // show/hide relevant info
                if (length - 1 < ajax_data.max_authorities) {
                    this.$el.find('.cannot-select-more').hide();
                }
            }
        },
    });

    Agora.AgoraSettingsView = Backbone.View.extend({
        initialize: function() {
            _.bindAll(this);

            Agora.renderAgoraTabs();
            app.modalDialog = new Agora.ModalDialogView();

            var text = $("#agora_short_description").text();
            var converter = new Showdown.converter();
            $("#agora_short_description").html(converter.makeHtml(text));

            this.agora_settings_form_view = new Agora.AgoraSettingsFormView();
        }
    });
}).call(this)

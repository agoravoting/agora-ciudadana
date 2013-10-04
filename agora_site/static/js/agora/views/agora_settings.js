(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.AgoraSettingsFormView = Backbone.View.extend({
        el: "#agora-settings-form",

        sendingData: false,

        events: {
            'click .available-choices li a': 'selectChoice',
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-agora-settings-form").html());
            this.templateAuthority = _.template($("#template-authority-item").html());
            this.render();
        },

        render: function() {
            this.$el.html(this.template(ajax_data));

            // shuffle options
            this.$el.find('.available-choices ul').shuffle();

            var self = this;
            var selection = [];
            // restore selected options from model if any
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

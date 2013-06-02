(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.UserSettingsFormView = Backbone.View.extend({
        el: "#user-settings-form",

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-user-settings-form").html());
            this.render();

            var metrics_profile = [
                ['#id_first_name', 'presence', gettext('This field is required')],
                ['#id_first_name', 'between:4:140', gettext('Must be between 4 and 140 characters long')],
            ];
            this.$el.find("#tab-profile form").nod(metrics_profile,
                {silentSubmit: true, broadcastError: true});
            this.$el.find("#tab-profile form").on('silentSubmit', this.saveProfile);
            this.$el.find("#tab-profile form").submit(function (e) { e.preventDefault(); });

            return this.$el;
        },

        sendingData: false,

        saveProfile: function(e) {
            e.preventDefault();
            if (this.sendingData) {
                return;
            }

            $(".btn[type=submit]").addClass("disabled");
            this.sendingData = true;

            var json = {
                'first_name': $('#id_first_name').val(),
                'short_description': $('#id_short_description').val(),
                'biography': $('#id_biography').val(),
            };
            var self = this;
            var jqxhr = $.ajax("/api/v1/user/settings/", {
                data: JSON.stringifyCompat(json),
                contentType : 'application/json',
                type: 'PUT',
            })
            .done(function(e) {
                window.location.reload(true);
            })
            .fail(function() {
                self.sendingData = false;
                $(".btn[type=submit]").removeClass("disabled");
                alert("Error saving settings");
            });

            return false;
        },

        render: function() {
            this.$el.html(this.template(ajax_data.user));
            this.delegateEvents();
            return this;
        }
    });

    Agora.UserSettingsView = Backbone.View.extend({
        initialize: function() {
            _.bindAll(this);
            this.user_settings_form_view = new Agora.UserSettingsFormView();
        }
    });
}).call(this)

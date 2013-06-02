(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.UserSettingsFormView = Backbone.View.extend({
        el: "#user-settings-form",

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-user-settings-form").html());
            this.render();

            // profile form
            var metrics_profile = [
                ['#id_first_name', 'presence', gettext('This field is required')],
                ['#id_first_name', 'between:4:140', gettext('Must be between 4 and 140 characters long')],
            ];
            this.$el.find("#tab-profile form").nod(metrics_profile,
                {silentSubmit: true, broadcastError: true});
            this.$el.find("#tab-profile form").on('silentSubmit', this.saveProfile);
            this.$el.find("#tab-profile form").submit(function (e) { e.preventDefault(); });

            // email form
            var metrics_email = [
                ['#id_email', 'email', gettext('Must be a valid email (RFC 822)') ]
            ];
            this.$el.find("#email_form").nod(metrics_email,
                {silentSubmit: true, broadcastError: true});
            this.$el.find("#email_form").on('silentSubmit', this.saveEmail);
            this.$el.find("#email_form").submit(function (e) { e.preventDefault(); });

            // password form
            var metrics_password = [
                ['#id_password1', 'presence', gettext('This field is required')],
                ['#id_password2', 'presence', gettext('This field is required')],
                ['#id_password1', 'min-length:4', gettext('At least 4 characters')],
                ['#id_password2', 'same-as:#id_password1', gettext('Your passwords do not match')]
            ];
            this.$el.find("#password_form").nod(metrics_password,
                {silentSubmit: true, broadcastError: true});
            this.$el.find("#password_form").on('silentSubmit', this.savePassword);
            this.$el.find("#password_form").submit(function (e) { e.preventDefault(); });

            // initialize language selector
            var lang = $("body").data('lang');
            var lang_name = $("#id_language li[data-langcode=" + lang + "] a").html();
            $("#id_language .current-item.inline").html(lang_name);

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
                alert("Error saving profile settings");
            });

            return false;
        },

        saveEmail: function(e) {
            e.preventDefault();
            if (this.sendingData) {
                return;
            }

            $(".btn[type=submit]").addClass("disabled");
            this.sendingData = true;

            var json = {
                'email': $('#id_email').val(),
                'email_updates': $('#id_email_updates').attr('checked') == 'checked',
            };
            var self = this;
            var jqxhr = $.ajax("/api/v1/user/settings/", {
                data: JSON.stringifyCompat(json),
                contentType : 'application/json',
                type: 'PUT',
            })
            .done(function(e) {
                self.sendingData = false;
                $(".btn[type=submit]").removeClass("disabled");
            })
            .fail(function() {
                self.sendingData = false;
                $(".btn[type=submit]").removeClass("disabled");
                alert("Error saving email settings");
            });

            return false;
        },

        savePassword: function(e) {
            e.preventDefault();
            if (this.sendingData) {
                return;
            }

            $(".btn[type=submit]").addClass("disabled");
            this.sendingData = true;

            var json = {
                'old_password': $('#id_current_password').val(),
                'password1': $('#id_password1').val(),
                'password2': $('#id_password2').val(),
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
                alert("Error saving password settings");
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

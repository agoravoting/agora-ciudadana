(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.UserSettingsFormView = Backbone.View.extend({
        el: "#user-settings-form",

        events: {
            'click #set_gravatar_mugshot': 'setGravatarMugshot',
            'click #set_initials_mugshot': 'setInitialsMugshot',
        },

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

            // image upload stuff
            $('#uploaded-avatar').change(function() {
                var file = this.files[0];
                name = file.name;
                size = file.size;
                type = file.type;

                if (!file.type.match(/image.*/) || size > 1024*100) {
                    alert("Not an image or too big");
                    return;
                }
                var formdata = false;
                if (window.FormData) {
                    formdata = new FormData();
                }

                if (window.FileReader) {
                    reader = new FileReader();
                    reader.readAsDataURL(file);
                }

                if (formdata) {
                    formdata.append("custom_avatar", file);
                    var self = this;
                    $.ajax("/api/v1/user/mugshot/", {
                        type: "POST",
                        data: formdata,
                        processData: false,
                        contentType: false
                    })
                    .done(function(e) {
                        window.location.reload(true);
                    })
                    .fail(function() {
                        self.sendingData = false;
                        alert("Error uploading mugshot");
                    });
                }
            });


            // username form
            var metrics_username = [
                ['#id_username', 'presence', gettext('This field is required')],
                ['#id_username', 'between:4:140', gettext('Must be between 4 and 140 characters long')],
            ];
            this.$el.find("#username_form").nod(metrics_username,
                {silentSubmit: true, broadcastError: true});
            this.$el.find("#username_form").on('silentSubmit', this.changeUsername);
            this.$el.find("#username_form").submit(function (e) { e.preventDefault(); });

            // remove account form
            $("#remove_account_btn").click(this.removeAccount);


            return this.$el;
        },

        sendingData: false,

        setGravatarMugshot: function(e) {
            e.preventDefault();
            if (this.sendingData) {
                return;
            }

            $(".btn[type=submit]").addClass("disabled");
            this.sendingData = true;

            var json = {
                'use_gravatar': true,
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

        setInitialsMugshot: function(e) {
            e.preventDefault();
            if (this.sendingData) {
                return;
            }

            $(".btn[type=submit]").addClass("disabled");
            this.sendingData = true;

            var json = {
                'use_initials': true,
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
                'username': $('#id_username').val(),
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
                'old_password': $('#id_current_password2').val()
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
                alert(gettext("Error saving email settings. Please check that the provided current pasword is valid. Or maybe the email the provided email is invalid or already in use."));
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
                alert("Error saving password settings. Please check that the provided current pasword is valid.");
            });

            return false;
        },

        changeUsername: function(e) {
            e.preventDefault();
            if (this.sendingData) {
                return;
            }

            var data = {"username": ajax_data.user.username };

            app.confirmChangeUsernameDialog = new Agora.ModalDialogView();
            var title = _.template($("#template-confirm_change_username_modal_dialog_title").html())();
            var body =  _.template($("#template-confirm_change_username_modal_dialog_body").html())();
            var footer = _.template($("#template-confirm_change_username_modal_dialog_footer").html())();


            var title2 = _.template($("#template-confirm_change_username_modal_dialog_title2").html())();
            var body2 =  _.template($("#template-confirm_change_username_modal_dialog_body2").html())(data);
            var footer2 = _.template($("#template-confirm_change_username_modal_dialog_footer2").html())();

            app.confirmChangeUsernameDialog.populate(title, body, footer);
            app.confirmChangeUsernameDialog.show();
            $("#confirm-change-username-action").click(function(e, self) {
                e.preventDefault();

                $("#modal-label").html(title2);
                $(".modal-body").html(body2);
                $(".modal-footer").html(footer2);

                $("#do-change-username-action").click(function(e, self) {
                    e.preventDefault();
                    if ($("#do-change-username-action").hasClass("disabled")) {
                       return false;
                    }

                    $("#do-change-username-action").addClass("disabled");
                    this.sendingData = true;

                    var json = {
                        'username': $('#id_username_modal_dialog').val(),
                    };
                    var self = this;
                    var jqxhr = $.ajax("/api/v1/user/settings/", {
                        data: JSON.stringifyCompat(json),
                        contentType : 'application/json',
                        type: 'PUT',
                    })
                    .done(function(e) {
                        self.sendingData = false;
                        $("#do-change-username-action").removeClass("disabled");
                        $("#modal_dialog").modal('hide');
                    })
                    .fail(function() {
                        self.sendingData = false;
                        $("#do-change-username-action").removeClass("disabled");
                        alert("Error changing username");
                        $("#modal_dialog").modal('hide');
                    });

                    return false;
                });

                return false;
            });

            return false;
        },

        removeAccount: function(e) {
            e.preventDefault();
            if (this.sendingData) {
                return;
            }

            app.confirmRemoveAccountDialog = new Agora.ModalDialogView();
            var title = _.template($("#template-remove_account_modal_dialog_title").html())();
            var body =  _.template($("#template-remove_account_modal_dialog_body").html())();
            var footer = _.template($("#template-remove_account_modal_dialog_footer").html())();

            app.confirmRemoveAccountDialog.populate(title, body, footer);
            app.confirmRemoveAccountDialog.show();
            var self = this;
            $("#confirm-remove-account-action").click(function(e) {
                e.preventDefault();
                self.sendingData = true;
                var json = {
                    'password': $("#remove_account_password").val()
                };
                var jqxhr = $.ajax("/api/v1/user/disable/", {
                    data: JSON.stringifyCompat(json),
                    contentType : 'application/json',
                    type: 'POST',
                })
                .done(function(e) {
                    window.location.reload(true);
                })
                .fail(function() {
                    self.sendingData = false;
                    alert("Error, possibly an invalid password");
                });

                return false;
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

(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.UserSettingsFormView = Backbone.View.extend({
        el: "#user-settings-form",

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-user-settings-form").html());
            this.render();

            return this.$el;
        },

        render: function() {
            this.$el.html(this.template({}));
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

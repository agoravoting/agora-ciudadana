(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.AgoraSettingsFormView = Backbone.View.extend({
        el: "#agora-settings-form",

        sendingData: false,

        events: {
        },

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-agora-settings-form").html());
            this.render();
        },

        render: function() {
            this.$el.html(this.template(ajax_data));
            this.delegateEvents();
            return this;
        }
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

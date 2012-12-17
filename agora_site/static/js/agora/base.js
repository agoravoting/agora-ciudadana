(function() {
    var Agora = this.Agora = {};
    var app = this.app = {};

    Agora.TopView = Backbone.View.extend({
        el: "#top-bar",

        events: {},

        initialize: function() {
            _.bindAll(this);
        }
    });

    Agora.MainView = Backbone.View.extend({
        el: "body",

        events: {
            "click a.action-form-link": "onActionFormLinkClicked"
        },

        initialize: function() {
            _.bindAll(this);

            $(document).ajaxStop(this.updateUi);
            this.updateUi();

            this.topBar = new Agora.TopView();
        },

        updateUi: function() {
            this.$("time.timeago").timeago();
        },

        onActionFormLinkClicked: function(event) {
            event.preventDefault();
            var target = $(event.currentTarget);
            this.$("#post-action-form").attr('action', target.attr('href'));
            this.$("#post-action-form").submit();
        }
    });

    app.main = new Agora.MainView();
}).call(this);

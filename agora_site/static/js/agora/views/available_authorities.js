(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.AuthoritiesListView = Agora.GenericListView.extend({
        el: "#auth-ul-list",
        templateEl: "#template-one-authority-item"
    });

    Agora.AvailableAuthoritiesView = Backbone.View.extend({
        el: "#available-authorities",

        initialize: function() {
            _.bindAll(this);

            // render main part
            this.template = _.template($("#template-available-authorities").html());
            this.$el.html(this.template({}));

            this.auth_list_view = new Agora.AuthoritiesListView();
        }
    });
}).call(this)
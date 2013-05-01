(function() {

    Agora.VotingBoothStartScreen = Backbone.View.extend({
        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth_start_screen").html());
            this.render();

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));
            var converter = new Showdown.converter();
            var self = this;
            this.$el.find('.markdown-readonly').each(function (index) {
                var data_id = $(this).data('id');
                $(this).html(converter.makeHtml(self.model.get(data_id)));
            });
            return this;
        },
    });

    Agora.VotingBooth = Backbone.View.extend({
        el: "#voting_booth",

        initialize: function() {
            _.bindAll(this);
            this.template = _.template($("#template-voting_booth").html());

            // ajax_data is a global variable
            this.model = new Agora.ElectionModel(ajax_data);
            this.render();

            return this.$el;
        },

        render: function() {
            // render template
            this.$el.html(this.template(this.model.toJSON()));

            this.startScreenView = new Agora.VotingBoothStartScreen({model: this.model});
            this.$el.find(".start-screen").append(this.startScreenView.render().el);

            return this;
        },
    });
}).call(this);

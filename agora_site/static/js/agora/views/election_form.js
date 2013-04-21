(function() {
    Agora.ElectionCreateForm = Backbone.View.extend({
        el: "div.top-form",

        initialize: function() {
            this.template = _.template($("#template-election_form").html())
            _.bindAll(this);
            Agora.ElectionModel = Backbone.Model.extend({});
            this.model = new Agora.ElectionModel({
                'name': '',
                'description': ''
            });
            this.$el.html(this.template(this.model));

            $('.datetimepicker').datetimepicker();
            $('div.top-form #schedule_voting_controls').toggle($('div.top-form #schedule_voting').is(':checked'));

            $('div.top-form #schedule_voting').click(function(){
                $('div.top-form #schedule_voting_controls').toggle(this.checked);
            });
        }
    });
}).call(this);

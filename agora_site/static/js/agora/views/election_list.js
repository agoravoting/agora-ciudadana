(function() {
    var ElectionInfinteView = Agora.GenericListView.extend({
        el: "#activity-list",
        templateEl: "#template-search-election-item",

        // Add gettext var
        renderItem: function(model) {
            var json = model.toJSON();
            json.election_at = interpolate(
                gettext('%(electionname)s at %(agora_full_name)s'),
                {
                    'electionname': json.pretty_name,
                    'agora_full_name': json.agora.full_name
                }, true);
            return this.template(json);
        }
    });

    Agora.ElectionListView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.infiniteListView = new ElectionInfinteView();
        }
    });
}).call(this);

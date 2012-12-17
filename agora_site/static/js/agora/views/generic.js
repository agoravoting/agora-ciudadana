(function() {
    var Agora = this.Agora,
        app = this.app;

    /*
     * Calendar widget with search features.
    */

    Agora.CalendarView = Backbone.View.extend({
        el: "#agora-calendar",

        events: {
            "keyup .election-search-query": "onSearchChange"
        },

        initialize: function() {
            _.bindAll(this);
            this.agoraTemplate = _.template($("#template-agora").html());
        },

        onSearchChange: function(event) {
            var target = $(event.currentTarget);
            console.log("onSearchChange: " + target.val());
        }
    });

    /*
     * Right side widget with small search.
     * Show a list of agoras.
    */

    Agora.AgoraListView = Backbone.View.extend({
        // el: ".agora-list"
        el: "#agora-list",

        initialize: function() {
            _.bindAll(this);
            this.electionTemplate = _.template($("#template-election").html());
        }
    });

    /*
     * Activity list block (Generic View).
     * Used on home and agora page.
    */

    Agora.ActivityListView = Backbone.View.extend({
        el: "#activity-list",

        initialize: function() {
            _.bindAll(this);
        }
    });
}).call(this);

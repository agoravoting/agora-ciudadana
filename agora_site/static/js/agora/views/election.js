(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.ElectionView = Backbone.View.extend({
        el: "div.election",

        initialize: function() {
            _.bindAll(this);
            // Only initialize on correct section of page exists.
            if ($("#activity-list").length > 0) {
                this.activityListView = new Agora.ActivityListView();
            }
        }
    });
}).call(this)

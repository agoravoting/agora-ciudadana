(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.UserView = Backbone.View.extend({
        el: "div.user",

        initialize: function() {
            _.bindAll(this);
            // Only initialize on correct section of page exists.
            if ($("#activity-list").length > 0) {
                this.activityListView = new Agora.ActivityListView();
            }
             this.agoralistView = new Agora.AgoraWidgetListView();
        }
    });
}).call(this)

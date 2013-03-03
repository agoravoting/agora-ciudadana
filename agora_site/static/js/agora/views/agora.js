(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.AgoraView = Backbone.View.extend({
        el: "div.agora",

        initialize: function() {
            _.bindAll(this);
            //this.calendarView = new Agora.CalendarWidgetView();

            // Only initialize on correct section of page exists.
            if (this.$("#activity-list").length > 0) {
                this.activityListView = new Agora.ActivityListView();
            }
        }
    });
}).call(this)

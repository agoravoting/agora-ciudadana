(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.HomeView = Backbone.View.extend({
        el: "div.home",

        initialize: function() {
            _.bindAll(this);
            this.calendarView = new Agora.CalendarWidgetView();
            this.agoralistView = new Agora.AgoraWidgetListView();
            this.activityListView = new Agora.ActivityListView();
        }
    });
}).call(this)

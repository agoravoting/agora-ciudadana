(function() {
    var Agora = this.Agora,
        app = this.app;

    /*
     * Agoras list widget scope.
     */

    (function() {
        var AgoraModel = Backbone.Model.extend({});
        var AgorasCollection = Backbone.Collection.extend({
            model: AgoraModel
        });

        Agora.AgoraWidgetListView = Backbone.View.extend({
            el: "#agora-list",

            initialize: function() {
                _.bindAll(this);
                this.agoraTemplate = _.template($("#template-agora").html());
                this.agorasCollection = new AgorasCollection();
                this.agorasCollection.on('reset', this.resetAgorasCollection);

                var ajax = new Ajax();
                ajax.on("success", this.initializeSuccess);
                ajax.get(this.$el.data('url'));
            },

            initializeSuccess: function(xhr) {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    this.agorasCollection.reset(data.objects);
                }
            },

            resetAgorasCollection: function(collection) {
                this.$(".last-agoras .list-container").empty();
                if (collection.length === 0) {
                    var emptyItem = this.make('ul', {'id':'no-agoras'}, gettext('No agoras found'));
                    this.$(".last-agoras .list-container").append(emptyItem);
                } else {
                    collection.each(this.addAgoraItem);
                }
            },

            addAgoraItem: function(model) {
                var dom = this.agoraTemplate(model.toJSON());
                this.$(".last-agoras .list-container").append(dom);
            }
        });
    }).call(this);

    Agora.HomeView = Backbone.View.extend({
        el: "div.home",

        initialize: function() {
            _.bindAll(this);
            this.calendarView = new Agora.CalendarWidgetView();
            this.agoralistView = new Agora.AgoraWidgetListView();
            this.activityListView = new Agora.InfiniteScrollListView();
        }
    });
}).call(this)

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

        events: {
            "click a.endless_more": "onMoreClicked"
        },

        initialize: function() {
            _.bindAll(this);
            $(window).scroll(this.infiniteScroll);
        },

        infiniteScroll: function() {
            var doc = $(document), win = $(window);
            var margin = this.$el.data('endless-smargin') || 1;

            if ((doc.height() - win.height() - win.scrollTop()) <= margin) {
                this.$("a.endless_more").click();
            }
        },

        onMoreClicked: function(event) {
            console.log("onMoreClicked");
            event.preventDefault();

            var target = $(event.currentTarget).hide();
            target.closest('.endless_container').find('.endless_loading').show();

            var data = "querystring_key=" + target.attr('rel').split(' ')[0];
            var ajax = new Ajax();

            ajax.on("success", this.loadMoreSuccess);

            ajax.setContext({target:target});
            ajax.get(target.attr('href'), data);
        },

        loadMoreSuccess: function(xhr, message, ctx) {
            var data = xhr.responseText;
            ctx.target.closest('.endless_container').before(data);
            ctx.target.closest('.endless_container').remove();
        }
    });
}).call(this);

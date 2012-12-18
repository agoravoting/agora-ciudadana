(function() {
    var Agora = this.Agora,
        app = this.app;

    /*
     * Agora calendar widget scope
    */

    (function() {
        var ElectionModel = Backbone.Model.extend({});
        var ElectionsCollection = Backbone.Collection.extend({
            model: ElectionModel
        });

        Agora.CalendarView = Backbone.View.extend({
            el: "#agora-calendar",

            events: {
                "keyup .election-search-query": "onSearchChange"
            },

            initialize: function() {
                _.bindAll(this);
                this.electionTemplate = _.template($("#template-election").html());
                this.electionsCollection = new ElectionsCollection();
                this.electionsCollection.on('reset', this.resetElectionsCollection);

                var ajax = new Ajax();
                ajax.on('success', this.initializeSuccess);
                ajax.get(this.$el.data('url'));

                // Debouncing
                this.onSearchChange = _.debounce(this.onSearchChange, 400);
            },

            initializeSuccess: function(xhr) {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    this.electionsCollection.reset(data.objects);
                }
            },

            onSearchChange: function(event) {
                var target = $(event.currentTarget);
                var data = {"q": target.val()};

                var ajax = new Ajax();
                ajax.on('success', this.initializeSuccess);
                ajax.get(this.$el.data('url'), data);
                console.log("onSearchChange: " + target.val());
            },

            resetElectionsCollection: function(collection) {
                this.$(".list-container").empty();
                collection.each(this.addElectionItem);
            },

            addElectionItem: function(model) {
                var dom = this.electionTemplate(model.toJSON());
                this.$(".list-container").append(dom);
            }
        });
    }).call(this);

    /*
     * Agoras list widget scope.
    */

    (function() {
        var AgoraModel = Backbone.Model.extend({});
        var AgorasCollection = Backbone.Collection.extend({
            model: AgoraModel
        });

        Agora.AgoraListView = Backbone.View.extend({
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

    /*
     * Generic view for all infinite scroll lists.
    */

    Agora.InfiniteScrollListView = Backbone.View.extend({
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

    /*
     * Generic view for all search pages.
    */

    Agora.GenericSearchView = Backbone.View.extend({
        el: "div.search",

        initialize: function() {
            _.bindAll(this);
            this.activityListView = new Agora.InfiniteScrollListView();
        }
    });
}).call(this);

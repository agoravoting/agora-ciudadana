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

        Agora.CalendarWidgetView = Backbone.View.extend({
            el: "#agora-calendar",

            events: {
                "keyup .election-search-query": "onSearchChange"
            },

            initialize: function() {
                _.bindAll(this);
                this.template = _.template($("#template-election").html());
                this.collection = new ElectionsCollection();
                this.collection.on('reset', this.resetCollection);

                var ajax = new Ajax();
                ajax.on('success', this.initializeSuccess);
                ajax.get(this.$el.data('url'));

                // Debouncing
                this.onSearchChange = _.debounce(this.onSearchChange, 400);
            },

            initializeSuccess: function(xhr) {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    console.log(data);
                    this.collection.reset(data.objects);
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

            resetCollection: function(collection) {
                this.$(".list-container").empty();
                collection.each(this.addItem);
            },

            addItem: function(model) {
                var dom = this.template(model.toJSON());
                this.$(".list-container").append(dom);
            }
        });
    }).call(this);

    /*
     * Generic view for all infinite scroll lists.
     * DEPRECATED
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

    (function() {
        var ItemModel = Backbone.Model.extend({});

        var ItemCollection = Backbone.Collection.extend({
            model: ItemModel
        });

        Agora.GenericListView = Backbone.View.extend({
            el: "#activity-list",

            events: {
                "click a.endless_more": "onMoreClicked"
            },

            setup: function() {
                this.url = this.$el.data('url');
                this.method = this.$el.data('method') || 'get';
            },

            setupTemplates: function() {
                if (this.templateEl !== undefined) {
                    this.template = _.template($(this.templateEl).html());
                }
            },

            initialize: function() {
                _.bindAll(this);
                this.firstLoadSuccess = false;
                this.finished = false;

                this.collection = new ItemCollection();
                this.collection.on('reset', this.collectionReset);
                this.collection.on('add', this.addItem);
                this.endlessDom = this.$(".endless-container");

                this.offset = 0;
                this.limit = 2;

                this.setup();
                this.setupTemplates();
                this.requestObjects();

                $(window).scroll(this.infiniteScroll);
            },

            requestObjects: function() {
                if (!this.finished) {
                    var ajax = new Ajax();
                    ajax.on('success', this.requestSuccess);

                    var params = _.extend({}, {limit:this.limit, offset: this.offset},
                                                                this.params || {});
                    this.offset += this.limit;

                    if (this.method === 'get') {
                        ajax.get(this.url, params);
                    } else if (this.method === 'post') {
                        ajax.post(this.url, params);
                    }
                }
            },

            setEndlesFinishDom: function() {
                this.endlessDom.find("a.endless_more").replaceWith("<span>No more results</span>");
            },

            requestSuccess: function(xhr) {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);

                    if (data.objects.length === 0) {
                        this.setEndlesFinishDom();
                        this.finished = true;
                    } else {
                        if (!this.firstLoadSuccess) {
                            this.firstLoadSuccess = true;
                            this.collection.reset(data.objects);
                        } else {
                            _.each(data.objects, function(item) {
                                this.collection.add(item);
                            }, this);
                        }

                        this.endlessDom.appendTo(this.$el);
                    }
                }
            },

            collectionReset: function(collection) {
                this.$el.empty();
                collection.each(this.addItem);
            },

            renderItem: function(model) {
                if (this.template !== undefined) {
                    return this.template(model.toJSON());
                } else {
                    return "<div>REIMPLEMENT THIS</div>";
                }
            },

            addItem: function(model) {
                var html = this.renderItem(model);
                this.$el.append(html);
            },

            infiniteScroll: function() {
                var doc = $(document), win = $(window);
                var margin = this.$el.data('margin') || 300;

                if ((doc.height() - win.height() - win.scrollTop()) <= margin) {
                    this.$("a.endless_more").click();
                }
            },

            onMoreClicked: function(event) {
                event.preventDefault();
                this.requestObjects();
            }
        });
    }).call(this);


    (function() {
        var AgoraListView = Agora.GenericListView.extend({
            el: "#activity-list",
            templateEl: "#template-search-agora-item"
        });

        Agora.AgoraListView = Backbone.View.extend({
            el: "div.search",

            initialize: function() {
                _.bindAll(this);
                this.infiniteListView = new AgoraListView();
            }
        });


        var ElectionListView = Agora.GenericListView.extend({
            el: "#activity-list",
            templateEl: "#template-search-election-item"
        });

        Agora.ElectionListView = Backbone.View.extend({
            el: "div.search",

            initialize: function() {
                _.bindAll(this);
                this.infiniteListView = new ElectionListView();
            }
        });
    }).call(this);
}).call(this);

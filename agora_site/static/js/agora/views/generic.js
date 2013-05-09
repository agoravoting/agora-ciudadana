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

                var data = collection.groupBy(function(item) {
                    var date = item.get('voting_extended_until_date') ||
                        item.get('voting_ends_at_date') ||
                        item.get('voting_starts_at_date');
                    if (date) {
                        return date.split("T")[0];
                    } else {
                        return null;
                    }
                });

                _.each(_.pairs(data), function(item) {
                    var key = item[0],
                        val = item[1];

                    var date = moment(key);
                    var dom = this.template({"datetime":date.format("LL"), "items": val});

                    this.$(".list-container").append(dom);
                }, this);

                if (collection.length === 0) {
                    this.$(".list-container").append(this.$("#no-elections"));
                }
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
                this.endlessDom.find("div.endless_loading").hide();

                this.offset = 0;
                this.limit = 20;

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

            setEndlessFinishDom: function() {
                this.endlessDom.find("a.endless_more").replaceWith(gettext("<span>No more results</span>"));
                this.endlessDom.find("div.endless_loading").hide();
            },

            requestSuccess: function(xhr) {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);

                    this.endlessDom.find("div.endless_loading").hide();
                    if (data.objects.length === 0) {
                        this.setEndlessFinishDom();
                        this.finished = true;
                    } else {
                        var doc = $(document), win = $(window);

                        if (!this.firstLoadSuccess) {
                            this.firstLoadSuccess = true;
                            this.collection.reset(data.objects);
                        } else {
                            this.$("a.endless_more").show();
                            _.each(data.objects, function(item) {
                                this.collection.add(item);
                            }, this);
                        }

                        this.endlessDom.appendTo(this.$el);

                        // if received less than the limit per page, it means
                        // there are no more items
                        if (data.objects.length < this.limit) {
                            this.setEndlessFinishDom();
                            this.finished = true;

                        // if received the limit per page, but the doc is still
                        // the same height as the window and scrollTop is 0,
                        // it means the window admits more elements and more
                        // elements can be fetch, so fetch those
                        } else if (doc.height() == win.height() &&
                            win.scrollTop() == 0) {
                            this.$("a.endless_more").click();
                            this.$("a.endless_more").hide();
                            this.endlessDom.find("div.endless_loading").show();
                        }
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

                if (!this.finished &&
                    (doc.height() - win.height() - win.scrollTop()) <= margin)
                {
                    this.$("a.endless_more").click();
                    this.$("a.endless_more").hide();
                    this.endlessDom.find("div.endless_loading").show();
                }
            },

            onMoreClicked: function(event) {
                event.preventDefault();
                this.requestObjects();
            }
        });
        Agora.ActivityListView = Agora.GenericListView.extend({
            el: "#activity-list",

            setup: function() {
                this.url = this.$el.data('url');
                this.method = this.$el.data('method') || 'get';
                this.templates = {}
            },

            renderItem: function(model) {
                var json = model.toJSON();
                json.actor.initials = this.getInitials(json);
                if (!this.templates[json.type_name]) {
                    this.templates[json.type_name] = _.template(
                        $('#template-action_' + json.type_name).html()
                            || '<#template-action_' + json.type_name
                            + ' not found>'
                    );
                }
                return this.templates[json.type_name](json);
            },

            getInitials: function(json) {
                if (json.actor.full_name && json.actor.full_name != json.actor.username) {
                    var initials = "";
                    var words = json.actor.full_name.split(" ");
                    _.each(words, function (word) {
                        initials += word[0].toUpperCase();
                    });
                    return initials;
                } else {
                    return json.actor.username[0].toUpperCase();
                }
            },
        });
    }).call(this);
}).call(this);

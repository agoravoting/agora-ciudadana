(function() {
    var Agora = this.Agora,
        app = this.app;

    Agora.HomeActivtyList = Agora.ActivityListView.extend({

        points: [],

        collectionReset: function(collection) {
            this.$el.empty();
            collection.each(this.addItem);


            this.slideShowElement = '#activity_items'; // this is where the infinite news scroll will be shown
            this.DELAY_SPEED = 4000; // specifies how much time between new items appear

            // Our projection.
            this.xy = d3.geo.mercator();
            this.geopath = d3.geo.path().projection(this.xy);

            this.states = d3.select("#home_worldmap_canvas").append("svg").append("g").attr("id", "states");

            this.currentSlide = 0; // keeps track of current slide
            this.slides = $('#activity-list > div'); // this is the original list of slides
            this.interval = setInterval(this.nextSlide, this.DELAY_SPEED); // used for setInerval

            // init
            var self = this;
            this.slides.each(function() {
                $(this).appendTo($(self.slideShowElement));
            });

            d3.json("/static/js/world-countries.json",
                function(collection) {

                    self.xy.scale(51);
                    var translate = self.xy.translate();
                    translate[0] = 160;
                    translate[1] = 110;
                    self.xy.translate(translate);

                    self.states
                        .selectAll("path")
                        .data(collection.features)
                        .enter().append("path")
                        .attr("d", self.geopath);

                    self.slides.each(function() {
                        self.geolocateElement($(this));
                    });
                }
            );

        },

        // Goes to the next slide
        nextSlide:function  () {
            //if the current slide is at the end, loop to the first slide.
            if (this.currentSlide >= this.slides.length -1) {
                this.currentSlide = 0;
            } else {
                this.currentSlide++;
            }

            // Add a new slide

            $(this.slideShowElement + ' > div').first().removeClass('activity-action-first');

            var newElement = $(this.slides[this.currentSlide]).clone().addClass('activity-action-first').hide();

            newElement.prependTo($(this.slideShowElement));
            newElement.animate({"height": "toggle", "opacity": "toggle"}, "slow");
            $(this.slideShowElement + ' > div').last().remove();

            this.geolocateElement(newElement);

            //if the auto slide advance is set, stop it, then start again.
            if (this.interval != null) {
                clearInterval(this.interval);
            }
            //Goes to next slide every couple of seconds.
            this.interval = setInterval(this.nextSlide, this.DELAY_SPEED);
        },

        geolocateElement:function (element)
        {
            var geodata = element.attr("geodata");

            if (geodata.length > 0) {
                geodata = geodata.substr(1, geodata.length - 2);
                geodata = geodata.split(",");
                // Make appear a point in the map
                var pos = [parseFloat(geodata[1]), parseFloat(geodata[0])];
                this.geolocate(pos);
            }
        },

        geolocate: function (pos)
        {
            pos = this.xy(pos);

            var point = this.points.pop()
            if (point) {
                d3.select(point)
                .transition()
                    .duration(100)
                    .style("fill-opacity", "0")
                    .each("end", function() {
                        d3.select(this).remove();
                    });
            }


            var self = this;
            function animateSecondStep()
            {
                self.points.push(this);
            }

            d3.select("#home_worldmap_canvas svg")
                .append("svg:circle")
                .style("fill-opacity", "0.1")
                .style("fill", "red")
                .attr("r", 10)
                .attr("cx", pos[0])
                .attr("cy", pos[1])
                .transition()
                .delay(0)
                .duration(1000)
                .attr("r", 1.5)
                .style("fill-opacity", "1")
                .each("end", animateSecondStep);
        },
    });

    Agora.HomeAnonymousView = Backbone.View.extend({
        el: "body",

        initialize: function() {
            _.bindAll(this);
            // Only initialize on correct section of page exists.
            if ($("#activity-list").length > 0) {
                this.activityListView = new Agora.HomeActivtyList();
            }
        },
    });
}).call(this)
